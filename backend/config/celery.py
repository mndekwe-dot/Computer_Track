"""The Celery application and the jobs that run on a clock.

Celery is one of four notification dispatch modes, and the one to use in
production. The outbox stays either way: a task queue that loses a message and
a committed database row are different guarantees, and what is being sent here
is sometimes the only warning a student gets that their laptop has left campus.

With no broker configured, `CELERY_TASK_ALWAYS_EAGER` runs every task in
process. That keeps a fresh clone and the test suite working without Redis,
and it never silently drops work - which is the failure mode that matters,
because nobody notices a notification that was never sent.

The tasks themselves live in each app's `tasks.py` and are found by
autodiscovery. Only the schedule is here, because a schedule is a statement
about the deployment as a whole.
"""

import os

from celery import Celery
from celery.schedules import schedule
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("computer_track")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.on_after_finalize.connect
def register_periodic_tasks(sender, **kwargs):
    """Recurring work, on intervals set in the environment.

    Every one of these used to be a crontab line somebody had to remember,
    documented in a README that a new administrator would not read until
    something had already gone wrong.

    Referenced by name rather than by import so this module does not pull the
    app registry in at import time, which is what breaks `celery -A config`
    when it is started before Django has finished loading.
    """
    intervals = (
        (settings.CELERY_BEAT_NOTIFICATIONS_SECONDS, "notifications.dispatch_pending"),
        (settings.CELERY_BEAT_AUDIT_ALERT_SECONDS, "accounts.check_audit_alerts"),
        (settings.CELERY_BEAT_PRUNE_SECONDS, "accounts.prune_audit_log"),
        (settings.CELERY_BEAT_PERMIT_SWEEP_SECONDS, "checkpoint.refresh_dashboard"),
    )
    for seconds, name in intervals:
        sender.add_periodic_task(schedule(seconds), sender.signature(name), name=name)
