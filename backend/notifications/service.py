"""Composing, queueing and draining notifications.

Nothing in here may ever raise into a caller. A gate decision and a computer
approval are the records that matter; telling somebody about them is best
effort, and a mail server outage must not turn into a 500 at the gate.

The wording is not here. It lives in the database and is edited by the
registration office - see notifications/templating.py. What is here is which
message gets queued when, for whom, and how it gets off the request path.
"""

import logging
import threading

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from campus.rules import rule

from .backends import PermanentFailure, deliver
from .models import Channel, Kind, Notification, Status
from .templating import compose

logger = logging.getLogger(__name__)


def max_attempts():
    """How many times a message is retried before it is given up on."""
    return getattr(settings, "NOTIFY_MAX_ATTEMPTS", 5)


def _backoff():
    return getattr(settings, "NOTIFY_RETRY_BACKOFF_SECONDS", 60)


def _branding():
    """The names and numbers every message can refer to."""
    return {
        "university": rule("branding.university_name"),
        "office": rule("branding.office_name"),
        "security_phone": rule("branding.security_phone"),
        "support_email": rule("branding.support_email"),
        "support_phone": rule("branding.support_phone"),
    }


def _student_context(student):
    if not student:
        return {"student_name": "", "student_first_name": "", "reg_number": ""}
    return {
        "student_name": student.full_name,
        # Used as a greeting, so it falls back to the full name rather than
        # opening a message with a blank line.
        "student_first_name": student.first_name or student.full_name,
        "reg_number": student.reg_number,
    }


def _device_context(device):
    if not device:
        return {"device": "", "serial": "", "brand": "", "asset_tag": ""}
    return {
        "device": device.label,
        "serial": device.serial_number,
        "brand": device.brand,
        # Rendered as a whole clause, so a device with no tag yields nothing
        # rather than a sentence trailing off after "Its asset tag is".
        "asset_tag": f" Its asset tag is {device.asset_tag}." if device.asset_tag else "",
    }


# ------------------------------------------------------------------ queueing


def _queue(kind, student, context, device=None):
    """Write the outbox rows for whichever contact details we hold.

    Email and SMS are composed separately from separate templates, because
    they are read in different places and one of them is billed by the
    segment.
    """
    if not student:
        return []

    rows = []
    if student.email:
        subject, body = compose(kind, Channel.EMAIL, context)
        if body.strip():
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
        _, body = compose(kind, Channel.SMS, context)
        if body.strip():
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
        # A rule rather than a setting: a university may want this off during
        # exam week, and that is not a decision worth a deployment.
        if not rule("gate.notify_owner_on_exit"):
            return []

        context = {
            **_branding(),
            **_student_context(scan.student),
            **_device_context(scan.device),
            "gate": scan.gate.name if scan.gate else "a campus gate",
            "time": timezone.localtime(scan.happened_at).strftime("%H:%M on %d %b"),
        }
        # The device may already be gone from the register by the time this
        # runs. The scan's own snapshot is what the log will always show.
        if not context["device"]:
            context["device"] = scan.device_label or scan.claimed_serial
            context["serial"] = scan.claimed_serial
        return _queue(Kind.EXIT, scan.student, context, scan.device)
    except Exception:
        logger.exception("Could not queue exit notification for scan %s", getattr(scan, "pk", "?"))
        return []


def notify_registration_approved(device):
    try:
        context = {**_branding(), **_student_context(device.owner), **_device_context(device)}
        return _queue(Kind.APPROVED, device.owner, context, device)
    except Exception:
        logger.exception("Could not queue approval notice for device %s", device.pk)
        return []


def notify_registration_rejected(device, reason):
    try:
        context = {
            **_branding(),
            **_student_context(device.owner),
            **_device_context(device),
            "reason": reason,
        }
        return _queue(Kind.REJECTED, device.owner, context, device)
    except Exception:
        logger.exception("Could not queue rejection notice for device %s", device.pk)
        return []


def notify_owner_of_missing_report(device, reason_label):
    """Tell the owner a hold was placed in their name.

    The public report blocks the computer immediately, because a stolen laptop
    is walking away while anyone deliberates. This message is the counterweight:
    a report the real owner did not make cannot stay quiet, and the person best
    placed to notice it is the owner.
    """
    if not device.owner:
        # University property has a department rather than a person; there is
        # nobody to write to.
        return []
    try:
        context = {
            **_branding(),
            **_student_context(device.owner),
            **_device_context(device),
            "report": reason_label.lower(),
        }
        return _queue(Kind.MISSING, device.owner, context, device)
    except Exception:
        # Never let a mail problem undo the block. The hold is the safety
        # critical half; the message is the courtesy half.
        logger.exception("Could not queue missing-report notice for device %s", device.pk)
        return []


def notify_staff(kind, recipients, subject, body):
    """A message to staff addresses rather than to a student record.

    Used by the audit alert and the suspicious-registration notice. These are
    not templated: they are read during an incident, and their wording is part
    of the procedure rather than a matter of house style.
    """
    rows = [
        Notification(
            kind=kind,
            channel=Channel.EMAIL,
            recipient=address,
            subject=subject,
            body=body,
        )
        for address in recipients
        if address
    ]
    if not rows:
        return []
    created = Notification.objects.bulk_create(rows)
    _schedule_dispatch()
    return created


# ----------------------------------------------------------------- draining


def send_one(notification):
    """Attempt a single delivery. Never raises."""
    notification.attempts += 1
    try:
        deliver(notification)
        notification.mark_sent()
        return True
    except Exception as error:
        permanent = isinstance(error, PermanentFailure)
        logger.warning(
            "Notification %s to %s failed (attempt %s, %s): %s",
            notification.pk,
            notification.recipient,
            notification.attempts,
            "permanent" if permanent else "will retry",
            error,
        )
        notification.mark_failed(
            error, max_attempts(), permanent=permanent, backoff_seconds=_backoff()
        )
        return False


def pending_queryset():
    """What is due to be sent right now.

    `next_attempt_at` in the future means a previous attempt failed and the
    backoff has not elapsed; picking those up anyway would turn the backoff
    into a no-op.
    """
    now = timezone.now()
    return Notification.objects.filter(
        status=Status.PENDING, attempts__lt=max_attempts()
    ).filter(Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)).order_by("created_at")


def dispatch_pending(limit=None):
    """Drain the outbox. Used by the worker, the Celery task and inline mode."""
    limit = limit or getattr(settings, "NOTIFY_BATCH_SIZE", 100)
    sent = failed = 0
    for notification in pending_queryset()[:limit]:
        if send_one(notification):
            sent += 1
        else:
            failed += 1
    return {"sent": sent, "failed": failed}


def _dispatch_mode():
    default = "inline" if settings.DEBUG else "celery"
    return getattr(settings, "NOTIFY_DISPATCH", default)


def _schedule_dispatch():
    """Get the sending off the request path, according to the configured mode.

    celery - hand to a worker after the transaction commits. The right answer
             for anything real: the request returns immediately, the work
             survives a restart, and retries are somebody else's problem.
    inline - send during the request. Convenient in development and tests;
             the only mode that puts a provider round trip on the request path.
    thread - a daemon thread after commit. For a single-process deployment
             with no broker to run.
    worker - do nothing here; `manage.py process_notifications` drains the
             outbox from cron.

    Every mode writes the outbox row first, so nothing is lost whichever is
    chosen. That is the point of the outbox: a broker that loses a message and
    a committed database row are different guarantees.
    """
    mode = _dispatch_mode()
    if mode == "worker":
        return

    if mode == "celery":
        def enqueue():
            try:
                from .tasks import dispatch_notifications

                dispatch_notifications.delay()
            except Exception:
                # A broker that is down must not fail the request that queued
                # the message. The row is committed; beat will drain it.
                logger.warning("Could not reach the Celery broker; leaving it to the worker")

        transaction.on_commit(enqueue)
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
