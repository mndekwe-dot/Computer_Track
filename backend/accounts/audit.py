"""Who looked up whom.

The register holds every student's name, photo, phone number and what
equipment they own, and any signed-in staff member can read all of it. That is
necessary for the job and uncomfortable for exactly the same reason: without a
record of reads, "a guard looked up their ex-girlfriend's address forty times"
is an unanswerable question.

This log makes it answerable. It records the *act* of looking, not the data
returned, so it stays small and does not duplicate the register itself.
"""

import logging

from django.db import models

logger = logging.getLogger(__name__)


class AuditAction(models.TextChoices):
    GATE_LOOKUP = "GATE_LOOKUP", "Gate lookup"
    SUGGEST = "SUGGEST", "Typeahead search"
    LIST_STUDENTS = "LIST_STUDENTS", "Browsed students"
    LIST_DEVICES = "LIST_DEVICES", "Browsed computers"
    EXPORT = "EXPORT", "Exported the gate log"


class AccessLog(models.Model):
    user = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="access_log"
    )
    # Kept as text as well, so the record still reads correctly if the account
    # is later deleted.
    username = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=20, choices=AuditAction.choices)
    query = models.CharField(max_length=200, blank=True)
    result_count = models.PositiveIntegerField(default=0)
    subject_reg_number = models.CharField(
        max_length=40, blank=True, help_text="Whose record was actually opened, when known."
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"], name="audit_user_created_idx"),
            models.Index(fields=["action", "-created_at"], name="audit_action_created_idx"),
        ]

    def __str__(self):
        return f"{self.username} {self.action} {self.query}".strip()


def client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        # Left-most entry is the original client.
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def record(request, action, query="", result_count=0, subject_reg_number=""):
    """Write an audit row. Never raises - auditing must not break the gate."""
    try:
        user = getattr(request, "user", None)
        if not (user and user.is_authenticated):
            return None
        return AccessLog.objects.create(
            user=user,
            username=user.username,
            action=action,
            query=(query or "")[:200],
            result_count=result_count,
            subject_reg_number=(subject_reg_number or "")[:40],
            ip_address=client_ip(request),
        )
    except Exception:
        logger.exception("Could not write audit record for %s", action)
        return None
