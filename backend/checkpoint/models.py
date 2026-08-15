from django.db import models


class Direction(models.TextChoices):
    IN = "IN", "Entering campus"
    OUT = "OUT", "Leaving campus"


class Verdict(models.TextChoices):
    ALLOWED = "ALLOWED", "Allowed"
    DENIED = "DENIED", "Denied"
    OVERRIDE = "OVERRIDE", "Allowed by override"
    UNREGISTERED = "UNREGISTERED", "Unregistered device"


class LookupMethod(models.TextChoices):
    REG_NUMBER = "REG_NUMBER", "Registration number"
    SERIAL = "SERIAL", "Serial number"
    ASSET_TAG = "ASSET_TAG", "Asset tag"
    QR = "QR", "QR sticker"
    MANUAL = "MANUAL", "Manual entry"


class ScanEvent(models.Model):
    """One decision made by a guard at a gate. Append-only audit trail."""

    device = models.ForeignKey(
        "devices.Device",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_events",
    )
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_events",
    )
    gate = models.ForeignKey(
        "campus.Gate", null=True, on_delete=models.SET_NULL, related_name="scan_events"
    )
    guard = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="scans_made"
    )
    direction = models.CharField(max_length=5, choices=Direction.choices)
    verdict = models.CharField(max_length=20, choices=Verdict.choices)
    method = models.CharField(
        max_length=20, choices=LookupMethod.choices, default=LookupMethod.REG_NUMBER
    )

    # Kept even when the device record is deleted later, so the log still reads
    # correctly years after the fact.
    claimed_serial = models.CharField(max_length=80, blank=True)
    claimed_reg_number = models.CharField(max_length=40, blank=True)
    device_label = models.CharField(max_length=160, blank=True)
    student_name = models.CharField(max_length=160, blank=True)

    permit = models.ForeignKey(
        "devices.TemporaryPermit",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="scan_events",
    )
    bearer_name = models.CharField(
        max_length=120, blank=True, help_text="Filled when someone other than the owner carries it."
    )
    override_reason = models.TextField(
        blank=True, help_text="Required when a guard lets a blocked device through."
    )
    notes = models.TextField(blank=True)

    client_reference = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        help_text="Idempotency key so a queued offline scan is never double-posted.",
    )
    client_timestamp = models.DateTimeField(
        null=True, blank=True, help_text="When the guard actually decided, if recorded offline."
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at", "gate"]),
            models.Index(fields=["device", "-created_at"]),
            models.Index(fields=["verdict"]),
        ]

    def __str__(self):
        return f"{self.get_direction_display()} · {self.device_label or self.claimed_serial} · {self.verdict}"

    @property
    def happened_at(self):
        """Real-world time of the decision, falling back to when it synced."""
        return self.client_timestamp or self.created_at

    def save(self, *args, **kwargs):
        # Snapshot the human-readable details at decision time.
        if self.device and not self.device_label:
            self.device_label = f"{self.device.label} · {self.device.serial_number}"
        if self.device and not self.claimed_serial:
            self.claimed_serial = self.device.serial_number
        if self.student:
            if not self.student_name:
                self.student_name = self.student.full_name
            if not self.claimed_reg_number:
                self.claimed_reg_number = self.student.reg_number
        super().save(*args, **kwargs)
