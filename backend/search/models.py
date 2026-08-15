from django.db import models


class SearchToken(models.Model):
    """One row per (searchable word, record) pair - a classic inverted index.

    Why this exists: the obvious `LIKE '%mug%'` cannot use a B-tree index,
    because the leading wildcard means the database has no idea where in the
    index to start. Every search becomes a full table scan, which is fine for
    the 40 rows in the demo data and hopeless for a real campus.

    Splitting each record into its words and indexing those turns the common
    case - "the guard is typing the start of a name, a reg number or a serial" - into `LIKE 'mug%'`, which *is* an indexed range scan.

    Both foreign keys are nullable and exactly one is set per row. They cascade,
    so deleting a student or a computer takes its tokens with it and the index
    cannot drift out of step with the records.
    """

    token = models.CharField(max_length=64)
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="search_tokens",
    )
    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="search_tokens",
    )

    class Meta:
        indexes = [
            # The prefix scan reads this index directly.
            models.Index(fields=["token"], name="search_token_idx"),
            models.Index(fields=["token", "student"], name="search_token_student_idx"),
            models.Index(fields=["token", "device"], name="search_token_device_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["token", "student"],
                condition=models.Q(student__isnull=False),
                name="uniq_token_per_student",
            ),
            models.UniqueConstraint(
                fields=["token", "device"],
                condition=models.Q(device__isnull=False),
                name="uniq_token_per_device",
            ),
            models.CheckConstraint(
                condition=models.Q(student__isnull=False, device__isnull=True)
                | models.Q(student__isnull=True, device__isnull=False),
                name="token_belongs_to_exactly_one_record",
            ),
        ]

    def __str__(self):
        return f"{self.token} -> {'student ' + str(self.student_id) if self.student_id else 'device ' + str(self.device_id)}"
