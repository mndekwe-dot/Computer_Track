"""Rebuild the search index from scratch.

    python manage.py rebuild_search_index

Needed after a bulk import that bypassed signals (loaddata, raw SQL, a
`bulk_create`), or after changing what gets tokenised.
"""

import time

from django.core.management.base import BaseCommand
from django.db import transaction

from devices.models import Device
from search.indexer import device_tokens, student_tokens
from search.models import SearchToken
from students.models import Student


class Command(BaseCommand):
    help = "Rebuild the inverted search index for every student and computer."

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch", type=int, default=500, help="Rows to write per bulk insert."
        )

    def handle(self, *args, **options):
        started = time.perf_counter()
        batch = options["batch"]

        with transaction.atomic():
            deleted = SearchToken.objects.all().delete()[0]
            self.stdout.write(f"Cleared {deleted} existing tokens.")

            rows = []
            students = Student.objects.all().only(
                "reg_number",
                "reg_number_key",
                "first_name",
                "last_name",
                "email",
                "phone",
                "national_id",
                "programme",
            )
            for student in students.iterator(chunk_size=batch):
                rows.extend(
                    SearchToken(token=token, student_id=student.pk)
                    for token in student_tokens(student)
                )
            student_rows = len(rows)

            for device in Device.objects.select_related("owner").iterator(chunk_size=batch):
                rows.extend(
                    SearchToken(token=token, device_id=device.pk)
                    for token in device_tokens(device)
                )

            SearchToken.objects.bulk_create(rows, batch_size=batch, ignore_conflicts=True)

        elapsed = time.perf_counter() - started
        self.stdout.write(
            self.style.SUCCESS(
                f"Indexed {student_rows} student tokens and {len(rows) - student_rows} "
                f"computer tokens in {elapsed:.2f}s."
            )
        )
