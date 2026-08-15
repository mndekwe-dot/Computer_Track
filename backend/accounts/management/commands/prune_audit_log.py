"""Delete audit entries older than the retention period.

    python manage.py prune_audit_log --dry-run
    python manage.py prune_audit_log

An audit log that grows forever is not a feature - it is an unbounded table
and, eventually, a privacy liability of its own. How long reads should be kept
is a policy decision, so it lives in one setting (`AUDIT_RETENTION_DAYS`,
default 365) rather than being hard-coded here.

Deliberately noisy: it reports what it is about to do and refuses a suspiciously
large deletion unless forced, because "prune" going wrong silently destroys the
one record that answers who looked at whom.
"""

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from accounts.audit import AccessLog

# Deleting most of the table is far more likely to be a mistake - a bad
# --days, a clock problem - than an intention.
SAFETY_FRACTION = 0.9


class Command(BaseCommand):
    help = "Delete audit log entries older than the retention period."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Override AUDIT_RETENTION_DAYS for this run.",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Report what would go, delete nothing."
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Proceed even if this would remove most of the log.",
        )
        parser.add_argument("--batch", type=int, default=5000)

    def handle(self, *args, **options):
        # `or` would be wrong here: --days 0 is falsy and would silently fall
        # back to the default instead of being rejected below.
        days = (
            options["days"]
            if options["days"] is not None
            else getattr(settings, "AUDIT_RETENTION_DAYS", 365)
        )
        if days < 1:
            self.stderr.write(self.style.ERROR("Retention must be at least one day."))
            return

        cutoff = timezone.now() - timedelta(days=days)
        total = AccessLog.objects.count()
        doomed = AccessLog.objects.filter(created_at__lt=cutoff)
        count = doomed.count()

        self.stdout.write(
            f"Retention: {days} days (anything before "
            f"{timezone.localtime(cutoff).strftime('%Y-%m-%d %H:%M')})"
        )
        self.stdout.write(f"Entries total: {total:,}   older than cutoff: {count:,}")

        if not count:
            self.stdout.write(self.style.SUCCESS("Nothing to prune."))
            return

        if options["dry_run"]:
            oldest = doomed.order_by("created_at").first()
            newest = doomed.order_by("-created_at").first()
            self.stdout.write(
                f"Would delete {count:,} entries, from "
                f"{timezone.localtime(oldest.created_at):%Y-%m-%d} to "
                f"{timezone.localtime(newest.created_at):%Y-%m-%d}."
            )
            self.stdout.write(self.style.WARNING("Dry run - nothing was deleted."))
            return

        if total and count / total > SAFETY_FRACTION and not options["force"]:
            self.stderr.write(
                self.style.ERROR(
                    f"Refusing: this would delete {count / total:.0%} of the audit log. "
                    f"Check --days, or pass --force if you really mean it."
                )
            )
            return

        # Batched so a large first prune does not hold one enormous transaction.
        removed = 0
        while True:
            ids = list(
                AccessLog.objects.filter(created_at__lt=cutoff).values_list("pk", flat=True)[
                    : options["batch"]
                ]
            )
            if not ids:
                break
            removed += AccessLog.objects.filter(pk__in=ids).delete()[0]

        self.stdout.write(
            self.style.SUCCESS(f"Pruned {removed:,} audit entries older than {days} days.")
        )
