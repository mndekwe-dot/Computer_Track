"""Composing, queueing and draining notifications.

Nothing in here may ever raise into a caller. A gate decision and a computer
approval are the records that matter; telling somebody about them is best
effort, and a mail server outage must not turn into a 500 at the gate.
"""

import logging
import threading

from django.conf import settings
from django.db import transaction

from .backends import deliver
from .models import Channel, Kind, Notification, Status

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 5


def _university():
    return getattr(settings, "UNIVERSITY_NAME", "the university")


# ---------------------------------------------------------------- composing


def _exit_message(scan):
    when = scan.happened_at.strftime("%H:%M on %d %b")
    gate = scan.gate.name if scan.gate else "a campus gate"
    return (
        f"Your computer ({scan.device_label or scan.claimed_serial}) was recorded leaving "
        f"{_university()} through {gate} at {when}. "
        f"If this was not you, contact campus security immediately."
    )


def _approved_message(device):
    tag = f" Its asset tag is {device.asset_tag}." if device.asset_tag else ""
    return (
        f"Good news - your {device.label} (serial {device.serial_number}) has been approved "
        f"and is now on the {_university()} computer register.{tag} "
        f"You may carry it through any gate. Collect its QR sticker from the registration "
        f"office if you have not already."
    )


def _rejected_message(device, reason):
    return (
        f"Your registration for {device.label} (serial {device.serial_number}) was not "
        f"approved.\n\nReason: {reason}\n\n"
        f"Please visit the registration office with the computer to sort this out. Until it is "
        f"registered, it will be held at the gate."
    )


# ------------------------------------------------------------------ queueing


def _queue(kind, subject, body, student, device=None):
    """Write the outbox rows for whichever contact details we hold."""
    if not getattr(settings, "NOTIFY_ON_EXIT", True) and kind == Kind.EXIT:
        return []
    if not student:
        return []

    rows = []
    if student.email:
        rows.append(
            Notification(
                kind=kind,
                channel=Channel.EMAIL,
                recipient=student.email,
                subject=subject,
                body=body,
                student=student,
                device=device,
            )
        )
    if student.phone:
        rows.append(
            Notification(
                kind=kind,
                channel=Channel.SMS,
                recipient=student.phone,
                subject="",
                body=body,
                student=student,
                device=device,
            )
        )
    if not rows:
        return []

    created = Notification.objects.bulk_create(rows)
    _schedule_dispatch()
    return created


def notify_owner_of_exit(scan):
    """Queue a warning that a computer has just left campus."""
    try:
        if scan.direction != "OUT":
            return []
        if scan.verdict not in {"ALLOWED", "OVERRIDE"}:
            return []
        return _queue(
            Kind.EXIT,
            "Your computer just left campus",
            _exit_message(scan),
            scan.student,
            scan.device,
        )
    except Exception:
        logger.exception("Could not queue exit notification for scan %s", getattr(scan, "pk", "?"))
        return []


def notify_registration_approved(device):
    try:
        return _queue(
            Kind.APPROVED,
            "Your computer registration was approved",
            _approved_message(device),
            device.owner,
            device,
        )
    except Exception:
        logger.exception("Could not queue approval notice for device %s", device.pk)
        return []


def notify_registration_rejected(device, reason):
    try:
        return _queue(
            Kind.REJECTED,
            "Your computer registration needs attention",
            _rejected_message(device, reason),
            device.owner,
            device,
        )
    except Exception:
        logger.exception("Could not queue rejection notice for device %s", device.pk)
        return []


# ----------------------------------------------------------------- draining


def send_one(notification):
    """Attempt a single delivery. Never raises."""
    notification.attempts += 1
    try:
        deliver(notification)
        notification.mark_sent()
        return True
    except Exception as error:
        logger.warning(
            "Notification %s to %s failed (attempt %s): %s",
            notification.pk,
            notification.recipient,
            notification.attempts,
            error,
        )
        notification.mark_failed(error, MAX_ATTEMPTS)
        return False


def dispatch_pending(limit=100):
    """Drain the outbox. Used by the worker command and by inline dispatch."""
    pending = Notification.objects.filter(
        status=Status.PENDING, attempts__lt=MAX_ATTEMPTS
    ).order_by("created_at")[:limit]

    sent = failed = 0
    for notification in pending:
        if send_one(notification):
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}


def _dispatch_mode():
    default = "inline" if settings.DEBUG else "worker"
    return getattr(settings, "NOTIFY_DISPATCH", default)


def _schedule_dispatch():
    """Get the sending off the request path, according to the configured mode.

    inline - send immediately. Convenient in development and tests; this is
              the only mode that puts SMTP back on the request path.
    thread - hand off to a daemon thread after the transaction commits. Good
              for a single-process deployment with no worker to run.
    worker - do nothing here; `manage.py process_notifications` drains the
              outbox. The right answer for anything real, and the point at
              which Celery or django-q would slot in instead.
    """
    mode = _dispatch_mode()
    if mode == "worker":
        return

    if mode == "inline":
        # After commit, so the rows are visible and a rollback sends nothing.
        transaction.on_commit(lambda: dispatch_pending())
        return

    if mode == "thread":
        def run():
            try:
                dispatch_pending()
            except Exception:
                logger.exception("Background notification dispatch failed")

        transaction.on_commit(lambda: threading.Thread(target=run, daemon=True).start())
