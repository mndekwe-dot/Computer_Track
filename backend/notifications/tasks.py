"""Sending, off the request path.

One task, deliberately. An earlier shape had a task per message, which meant a
provider outage produced one queued task per student and a thundering retry
storm when it came back. Draining a batch means the outbox decides the order
and the backoff, and the queue holds one item however many messages are
waiting.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="notifications.dispatch_pending", ignore_result=True)
def dispatch_notifications(limit=None):
    """Drain what is due. Safe to run concurrently with itself.

    Two workers picking up the same row would send twice, which for an SMS is
    a real cost. `send_one` increments `attempts` and writes the status before
    the next worker reads it, so the window is small; if duplicates ever
    matter more than latency, this is where a `select_for_update(skip_locked)`
    belongs.
    """
    from .service import dispatch_pending

    result = dispatch_pending(limit=limit)
    if result["failed"]:
        logger.info("Outbox drain: %s sent, %s failed", result["sent"], result["failed"])
    return result
