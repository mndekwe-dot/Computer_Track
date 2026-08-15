from django.contrib.auth.models import AbstractUser
from django.db import models


class Role(models.TextChoices):
    ADMIN = "ADMIN", "System administrator"
    REGISTRAR = "REGISTRAR", "Registration officer"
    GUARD = "GUARD", "Security guard"


class User(AbstractUser):
    """Staff account. Students do not log in - they are records, not users.

    Students reach the system only through the public registration form, which
    is unauthenticated by design (see students/public.py).
    """

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUARD)
    staff_number = models.CharField(max_length=40, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    default_gate = models.ForeignKey(
        "campus.Gate",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_staff",
        help_text="Gate this guard normally works at. Pre-selected in the console.",
    )

    class Meta:
        ordering = ("first_name", "last_name", "username")

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_admin_role(self):
        return self.role == Role.ADMIN or self.is_superuser

    @property
    def can_manage_records(self):
        """Registrars and admins may create/edit students and devices."""
        return self.is_admin_role or self.role == Role.REGISTRAR


# Defined in accounts/audit.py to keep the rationale beside the model, imported
# here so the app registry and makemigrations find it.
from .audit import AccessLog, AuditAction  # noqa: E402,F401
