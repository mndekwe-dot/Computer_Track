"""Look for accounts reading the register far above their own norm.

    python manage.py check_audit_alerts --dry-run
    python manage.py check_audit_alerts

Run hourly from cron. Alerts are queued through the notification outbox, so a
mail outage delays them rather than losing them.
"""

from django.conf import settings
from django.core.management.base import BaseCommand

from accounts.alerting import find_unusual_activity, raise_alerts


class Command(BaseCommand):
    help = "Email the security office about unusual register read volume."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true", help="Report findings, send nothing."
        )

    def handle(self, *args, **options):
        if options["dry_run"]:
            findings = find_unusual_activity()
            if not findings:
                self.stdout.write(self.style.SUCCESS("Nothing unusual."))
                return
            for finding in findings:
                ratio = "no history" if finding["ratio"] is None else f"{finding['ratio']}x usual"
                self.stdout.write(
                    f"  {finding['username']}: {finding['reads']} reads "
                    f"in {finding['window_hours']}h ({ratio})"
                )
            self.stdout.write(self.style.WARNING("Dry run - nothing sent."))
            return

        if not getattr(settings, "AUDIT_ALERT_RECIPIENTS", []):
            self.stderr.write(
                self.style.WARNING(
                    "AUDIT_ALERT_RECIPIENTS is empty - set it in .env or no alert can be sent."
                )
            )

        raised = raise_alerts()
        if not raised:
            self.stdout.write(self.style.SUCCESS("Nothing unusual (or still in cooldown)."))
            return
        for finding in raised:
            self.stdout.write(f"  alerted on {finding['username']} ({finding['reads']} reads)")
        self.stdout.write(self.style.SUCCESS(f"Raised {len(raised)} alert(s)."))
