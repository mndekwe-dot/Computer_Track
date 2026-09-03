from datetime import timedelta

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
    MISSING = "MISSING", "Computer reported missing"
    # Both of these go to staff rather than to a student, so `student` and
    # `device` stay null on them.
    AUDIT_ALERT = "AUDIT_ALERT", "Unusual register activity"
    SUSPICIOUS = "SUSPICIOUS", "Registration worth a second look"


# Which kinds a registrar may reword. AUDIT_ALERT and SUSPICIOUS are excluded
# on purpose: they are read by staff during an incident, and their wording is
# part of the procedure rather than a matter of tone.
EDITABLE_KINDS = [Kind.EXIT, Kind.APPROVED, Kind.REJECTED, Kind.MISSING]


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
    # When this may next be tried. Set on failure so a provider having a bad
    # minute is backed off rather than hammered once a minute by the worker.
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status", "created_at"], name="notif_status_created_idx"),
            models.Index(fields=["status", "next_attempt_at"], name="notif_status_retry_idx"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} to {self.recipient} ({self.status})"

    def mark_sent(self):
        self.status = Status.SENT
        self.sent_at = timezone.now()
        self.next_attempt_at = None
        self.save(
            update_fields=["status", "sent_at", "attempts", "last_error", "next_attempt_at"]
        )

    def mark_failed(self, error, max_attempts, permanent=False, backoff_seconds=60):
        """Record a failed attempt and decide whether there will be another.

        `permanent` matters more than the attempt count. An address that does
        not exist, an unverified sending domain, a phone number that is not a
        phone number: none of those get better on the fifth try, and retrying
        them costs money on SMS and sender reputation on email.
        """
        self.last_error = str(error)[:2000]
        if permanent or self.attempts >= max_attempts:
            self.status = Status.FAILED
            self.next_attempt_at = None
        else:
            # Kept PENDING so the worker picks it up again, but not before the
            # backoff has passed. Linear rather than exponential: five attempts
            # spread over a quarter of an hour is the right shape for a message
            # somebody is waiting on.
            self.status = Status.PENDING
            self.next_attempt_at = timezone.now() + timedelta(
                seconds=backoff_seconds * self.attempts
            )
        self.save(update_fields=["status", "attempts", "last_error", "next_attempt_at"])


class NotificationTemplate(models.Model):
    """The wording of one kind of message on one channel.

    Separate rows for email and SMS rather than one body used for both. They
    are not the same message written twice: an email can afford a greeting and
    a paragraph of explanation, and an SMS is billed by the segment and read
    on a lock screen. Forcing one text to serve both makes the email curt and
    the SMS expensive.

    See notifications/templating.py for the placeholders and the fallbacks.
    """

    kind = models.CharField(max_length=20, choices=Kind.choices)
    channel = models.CharField(max_length=10, choices=Channel.choices)
    subject = models.CharField(max_length=200, blank=True, help_text="Email only.")
    body = models.TextField()
    is_active = models.BooleanField(
        default=True, help_text="Turn off to fall back to the built-in wording."
    )
    updated_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="templates_edited",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("kind", "channel")
        constraints = [
            models.UniqueConstraint(fields=["kind", "channel"], name="one_template_per_channel")
        ]

    def __str__(self):
        return f"{self.get_kind_display()} ({self.get_channel_display()})"
