import re

from django.db import models


def normalise_reg_number(value):
    """Fold the many ways a reg number gets typed into one canonical form.

    Guards type in a hurry and students say their number out loud, so
    "218 001 234", "218-001-234" and "218001234" must all find the same record.
    """
    return re.sub(r"[\s\-/_.]", "", (value or "")).upper()


class StudentStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    GRADUATED = "GRADUATED", "Graduated"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Student(models.Model):
    reg_number = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        help_text="Registration number exactly as printed on the student ID.",
    )
    reg_number_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Normalised reg number used for lookups.",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    national_id = models.CharField(max_length=40, blank=True)
    department = models.ForeignKey(
        "campus.Department",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="students",
    )
    programme = models.CharField(max_length=120, blank=True)
    year_of_study = models.PositiveSmallIntegerField(null=True, blank=True)
    photo = models.ImageField(upload_to="students/", null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=StudentStatus.choices, default=StudentStatus.ACTIVE
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("last_name", "first_name")
        indexes = [models.Index(fields=["last_name", "first_name"])]

    def __str__(self):
        return f"{self.reg_number} - {self.full_name}"

    def save(self, *args, **kwargs):
        self.reg_number = (self.reg_number or "").strip().upper()
        self.reg_number_key = normalise_reg_number(self.reg_number)
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_clear_to_pass(self):
        """A suspended or withdrawn student should not be waved through."""
        return self.status == StudentStatus.ACTIVE
