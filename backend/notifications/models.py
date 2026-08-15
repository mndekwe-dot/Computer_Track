from django.db import models
from django.utils import timezone


class Channel(models.TextChoices):
    EMAIL = "EMAIL", "Email"
    SMS = "SMS", "SMS"


class Status(models.TextChoices):
    PENDING = "PENDING", "Waiting to send"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class Kind(models.TextChoices):
    EXIT = "EXIT", "Computer left campus"
    APPROVED = "APPROVED", "Registration approved"
    REJECTED = "REJECTED", "Registration rejected"
    # Goes to the security office rather than a student, so `student` and
    # `device` stay null on these.
    AUDIT_ALERT = "AUDIT_ALERT", "Unusual register activity"


class Notification(models.Model):
    """A message waiting to be sent - a transactional outbox.

    Notifications used to go out inline, inside the request that recorded a
    gate scan. That put an SMTP round trip on the critical path of the one
    action that must never be slow, and a mail server having a bad afternoon
    meant the message was simply lost.

    Writing a row instead costs about as much as the scan itself, commits in
    the same transaction as the thing it describes, and survives a restart. A
    worker drains the table afterwards and retries what failed.

    Swapping this for Celery or django-q later means changing only `dispatch`
    in service.py - the outbox stays either way, because a broker that loses a
    message and a database row that does not are different guarantees.
    """

    kind = models.CharField(max_length=20, choices=Kind.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    recipient = models.CharField(max_length=254, help_text="Email address or phone number.")
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()

    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )
    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="notifications",
    )

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=["status", "created_at"], name="notif_status_created_idx")]

    def __str__(self):
        return f"{self.get_kind_display()} to {self.recipient} ({self.status})"

    def mark_sent(self):
        self.status = Status.SENT
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "sent_at", "attempts", "last_error"])

    def mark_failed(self, error, max_attempts):
        self.last_error = str(error)[:2000]
        # Kept PENDING while retries remain, so the worker picks it up again.
        self.status = Status.FAILED if self.attempts >= max_attempts else Status.PENDING
        self.save(update_fields=["status", "attempts", "last_error"])
