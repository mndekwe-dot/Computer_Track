"""Spotting an account reading the register far more than it usually does.

A flat "more than N lookups is suspicious" threshold is close to useless here:
the Main Gate guard on a Monday morning legitimately does ten times the reads
of the Service Gate guard on a Sunday. One number cannot be both.

So each account is compared against **its own** recent baseline. A guard who
suddenly reads five times their normal daily volume is interesting whatever
that normal is. A fixed floor sits underneath, so a brand new account with no
history cannot trip the ratio on three lookups.

Two deliberate limits:
 - Only reads are counted, not writes. This is about who is *looking*.
 - An account is alerted about at most once per cooldown window, so a busy
    day produces one email and not a hundred.
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from .audit import AccessLog

logger = logging.getLogger(__name__)


def _config():
    return {
        "window_hours": getattr(settings, "AUDIT_ALERT_WINDOW_HOURS", 24),
        "baseline_days": getattr(settings, "AUDIT_ALERT_BASELINE_DAYS", 14),
        "multiplier": getattr(settings, "AUDIT_ALERT_MULTIPLIER", 5.0),
        "floor": getattr(settings, "AUDIT_ALERT_FLOOR", 200),
        "cooldown_hours": getattr(settings, "AUDIT_ALERT_COOLDOWN_HOURS", 24),
        "recipients": getattr(settings, "AUDIT_ALERT_RECIPIENTS", []),
    }


def find_unusual_activity(now=None):
    """Accounts reading far above their own recent norm. Returns a list of dicts."""
    config = _config()
    now = now or timezone.now()
    window_start = now - timedelta(hours=config["window_hours"])
    baseline_start = window_start - timedelta(days=config["baseline_days"])

    recent = (
        AccessLog.objects.filter(created_at__gte=window_start)
        .values("user_id", "username")
        .annotate(reads=Count("id"))
    )

    findings = []
    for row in recent:
        reads = row["reads"]
        # The floor stops a new account with no history alerting on nothing.
        if reads < config["floor"]:
            continue

        prior = AccessLog.objects.filter(
            user_id=row["user_id"],
            created_at__gte=baseline_start,
            created_at__lt=window_start,
        ).count()
        # Their usual volume over the same length of window.
        periods = max(
            1.0,
            (config["baseline_days"] * 24) / config["window_hours"],
        )
        baseline = prior / periods

        # No history at all: the floor alone decides.
        ratio = (reads / baseline) if baseline > 0 else float("inf")
        if baseline > 0 and ratio < config["multiplier"]:
            continue

        findings.append(
            {
                "user_id": row["user_id"],
                "username": row["username"],
                "reads": reads,
                "baseline": round(baseline, 1),
                "ratio": None if baseline == 0 else round(ratio, 1),
                "window_hours": config["window_hours"],
            }
        )

    return sorted(findings, key=lambda item: item["reads"], reverse=True)


def _recently_alerted(username, cooldown_hours):
    from notifications.models import Kind, Notification

    since = timezone.now() - timedelta(hours=cooldown_hours)
    return Notification.objects.filter(
        kind=Kind.AUDIT_ALERT, body__contains=username, created_at__gte=since
    ).exists()


def _message(finding):
    if finding["ratio"] is None:
        rate = "with no prior history for comparison"
    else:
        rate = (
            f"about {finding['ratio']}x their usual "
            f"({finding['baseline']} in a typical {finding['window_hours']}h)"
        )
    return (
        f"Account '{finding['username']}' made {finding['reads']} register reads in the last "
        f"{finding['window_hours']} hours - {rate}.\n\n"
        f"This is not evidence of anything on its own; a shift change or a busy open day looks "
        f"the same. It is worth a look in the Read Audit Log under Administration, filtered to "
        f"that account.\n\n"
        f"To stop these, adjust AUDIT_ALERT_MULTIPLIER or AUDIT_ALERT_FLOOR."
    )


def raise_alerts(now=None):
    """Queue an alert per unusual account. Returns what was raised."""
    from notifications.models import Channel, Kind, Notification
    from notifications.service import _schedule_dispatch

    config = _config()
    recipients = config["recipients"]
    if not recipients:
        logger.info("Audit alerting is on but AUDIT_ALERT_RECIPIENTS is empty; nothing sent.")
        return []

    raised = []
    for finding in find_unusual_activity(now=now):
        if _recently_alerted(finding["username"], config["cooldown_hours"]):
            continue

        body = _message(finding)
        Notification.objects.bulk_create(
            [
                Notification(
                    kind=Kind.AUDIT_ALERT,
                    channel=Channel.EMAIL,
                    recipient=address,
                    subject=f"Unusual register activity: {finding['username']}",
                    body=body,
                )
                for address in recipients
            ]
        )
        raised.append(finding)

    if raised:
        _schedule_dispatch()
    return raised
