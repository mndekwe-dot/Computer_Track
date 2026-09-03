"""Scheduled audit housekeeping.

Both of these wrap an existing management command rather than reimplementing
it. The commands carry safety checks worth keeping - `prune_audit_log` refuses
to delete most of the table without `--force`, which is exactly the mistake an
unattended scheduled job is most likely to make.
"""

import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(name="accounts.check_audit_alerts", ignore_result=True)
def check_audit_alerts():
    from .alerting import raise_alerts

    raised = raise_alerts()
    if raised:
        logger.info("Raised %s audit alert(s)", len(raised))
    return len(raised)


@shared_task(name="accounts.prune_audit_log", ignore_result=True)
def prune_audit_log():
    call_command("prune_audit_log")
