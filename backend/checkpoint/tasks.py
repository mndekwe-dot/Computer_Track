"""Keeping the dashboard cheap.

The dashboard is a wall screen in the security office. It is left open all
day, refetches on a timer, and every load runs a dozen aggregates over the
whole scan table. Recomputing that per viewer is the single most expensive
thing this system does, and none of it needs to be to the second.

So it is cached, and this task refreshes it on a schedule. That way the cost
is paid once by a background worker rather than by whichever guard happens to
open the page after the cache expired.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="checkpoint.refresh_dashboard", ignore_result=True)
def refresh_dashboard():
    from .stats import refresh_dashboard_cache

    refresh_dashboard_cache()
    return True
