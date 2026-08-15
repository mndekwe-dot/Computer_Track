"""Drain the notification outbox.

    python manage.py process_notifications            # one pass, then exit
    python manage.py process_notifications --loop     # stay running

Run the one-shot form from cron every minute, or the looping form under
systemd or supervisor. Either way the sending happens outside the request that
recorded the gate scan.
"""

import time

from django.core.management.base import BaseCommand

from notifications.models import Notification, Status
from notifications.service import MAX_ATTEMPTS, dispatch_pending


class Command(BaseCommand):
    help = "Send queued notifications."

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true", help="Keep running.")
        parser.add_argument("--interval", type=int, default=15, help="Seconds between passes.")
        parser.add_argument("--limit", type=int, default=100, help="Messages per pass.")
        parser.add_argument(
            "--retry-failed",
            action="store_true",
            help="Reset permanently failed messages back to pending and try again.",
        )

    def handle(self, *args, **options):
        if options["retry_failed"]:
            reset = Notification.objects.filter(status=Status.FAILED).update(
                status=Status.PENDING, attempts=0, last_error=""
            )
            self.stdout.write(f"Reset {reset} failed notification(s) for another attempt.")

        while True:
            result = dispatch_pending(limit=options["limit"])
            if result["sent"] or result["failed"]:
                self.stdout.write(
                    f"sent {result['sent']}, failed {result['failed']}"
                )
            if not options["loop"]:
                break
            time.sleep(options["interval"])

        stuck = Notification.objects.filter(
            status=Status.FAILED, attempts__gte=MAX_ATTEMPTS
        ).count()
        if stuck:
            self.stdout.write(
                self.style.WARNING(
                    f"{stuck} notification(s) gave up after {MAX_ATTEMPTS} attempts. "
                    f"Re-run with --retry-failed once the cause is fixed."
                )
            )
