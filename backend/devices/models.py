import re
import uuid

from django.db import models
from django.utils import timezone


def normalise_serial(value):
    """Serials get read off tiny stickers - ignore spacing and case."""
    return re.sub(r"[\s\-]", "", (value or "")).upper()


class DeviceType(models.TextChoices):
    LAPTOP = "LAPTOP", "Laptop"
    TABLET = "TABLET", "Tablet"
    DESKTOP = "DESKTOP", "Desktop / tower"
    MONITOR = "MONITOR", "Monitor"
    PROJECTOR = "PROJECTOR", "Projector"
    OTHER = "OTHER", "Other equipment"


class Ownership(models.TextChoices):
    """Who the equipment belongs to.

    Student-owned equipment and university property are checked at the same
    gate by the same guard, but the question being asked is different. For a
    laptop it is "does this belong to the person carrying it". For a projector
    it is "is this authorised to leave at all". Same register, two rules.
    """

    STUDENT = "STUDENT", "Student-owned"
    UNIVERSITY = "UNIVERSITY", "University property"


class DeviceStatus(models.TextChoices):
    PENDING = "PENDING", "Pending approval"
    ACTIVE = "ACTIVE", "Active"
    LOST = "LOST", "Reported lost"
    STOLEN = "STOLEN", "Reported stolen"
    RETIRED = "RETIRED", "Retired"


class Device(models.Model):
    """A computer registered to a student and recognised at the gates."""

    uid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    serial_number = models.CharField(max_length=80, unique=True)
    serial_key = models.CharField(max_length=80, unique=True, db_index=True, editable=False)
    asset_tag = models.CharField(
        max_length=40,
        unique=True,
        null=True,
        blank=True,
        help_text="University sticker code applied at registration.",
    )
    device_type = models.CharField(
        max_length=20, choices=DeviceType.choices, default=DeviceType.LAPTOP
    )
    brand = models.CharField(max_length=60)
    model_name = models.CharField(max_length=80, blank=True)
    colour = models.CharField(max_length=40, blank=True)
    distinguishing_marks = models.CharField(
        max_length=200,
        blank=True,
        help_text="Stickers, cracks, engravings - what the guard can see at a glance.",
    )
    ownership = models.CharField(
        max_length=20, choices=Ownership.choices, default=Ownership.STUDENT, db_index=True
    )
    # Null for university property, which belongs to a department rather than
    # to a person. Everything that reads this has to cope with None.
    owner = models.ForeignKey(
        "students.Student",
        on_delete=models.PROTECT,
        related_name="devices",
        null=True,
        blank=True,
    )
    # University property only: the department that owns it and the member of
    # staff answerable for it. A guard needs a name to call when a projector
    # turns up at a gate at nine at night.
    department = models.ForeignKey(
        "campus.Department",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment",
    )
    custodian_name = models.CharField(max_length=120, blank=True)
    photo = models.ImageField(upload_to="devices/", null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=DeviceStatus.choices, default=DeviceStatus.ACTIVE
    )
    is_archived = models.BooleanField(
        default=False, help_text="Hidden from normal lists without deleting the audit trail."
    )
    notes = models.TextField(blank=True)
    registered_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registered_devices",
    )
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-registered_at",)
        indexes = [models.Index(fields=["status", "is_archived"])]

    def __str__(self):
        return f"{self.brand} {self.model_name} · {self.serial_number}"

    def save(self, *args, **kwargs):
        self.serial_number = (self.serial_number or "").strip().upper()
        self.serial_key = normalise_serial(self.serial_number)
        self.asset_tag = (self.asset_tag or "").strip().upper() or None
        super().save(*args, **kwargs)

    @property
    def label(self):
        parts = [self.brand, self.model_name]
        return " ".join(p for p in parts if p) or self.get_device_type_display()

    @property
    def active_flags(self):
        return self.flags.filter(is_active=True)

    def blocking_reasons(self):
        """Everything that should stop this device leaving, in plain language.

        Returned as a list so the console can show every problem at once
        instead of the guard discovering them one at a time.
        """
        reasons = []
        if self.status == DeviceStatus.STOLEN:
            reasons.append("This device is reported STOLEN. Hold it and call security control.")
        elif self.status == DeviceStatus.LOST:
            reasons.append("This device is reported LOST by its owner.")
        elif self.status == DeviceStatus.PENDING:
            reasons.append("Registration is still pending approval by the registration office.")
        elif self.status == DeviceStatus.RETIRED:
            reasons.append("This device was retired from the register.")
        for flag in self.active_flags:
            reasons.append(f"{flag.get_reason_display()}: {flag.details or 'no details given'}")
        if self.owner and not self.owner.is_clear_to_pass:
            reasons.append(
                f"Owner status is {self.owner.get_status_display()}, not active."
            )
        return reasons

    def exit_restrictions(self):
        """Reasons this may not *leave*, as distinct from being blocked outright.

        Kept separate from `blocking_reasons` because direction matters here
        and nowhere else. University property returning to campus must not be
        stopped for the want of a gate pass; the same projector on its way out
        must be.
        """
        if self.ownership != Ownership.UNIVERSITY:
            return []
        if self.valid_permits().exists():
            return []
        return [
            "University property. It needs a gate pass before it can leave campus. "
            "Issue one under Permits, or record an override with a reason."
        ]

    @property
    def is_blocked(self):
        return bool(self.blocking_reasons())

    def valid_permits(self):
        now = timezone.now()
        return self.permits.filter(is_revoked=False, valid_from__lte=now, valid_to__gte=now)


class FlagReason(models.TextChoices):
    STOLEN = "STOLEN", "Reported stolen"
    LOST = "LOST", "Reported lost"
    OWNERSHIP_DISPUTE = "OWNERSHIP_DISPUTE", "Ownership dispute"
    UNPAID_FEES = "UNPAID_FEES", "Finance hold"
    DISCIPLINARY = "DISCIPLINARY", "Disciplinary hold"
    OTHER = "OTHER", "Other"


class DeviceFlag(models.Model):
    """A hold placed on a device. Any active flag blocks it at every gate."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="flags")
    reason = models.CharField(max_length=30, choices=FlagReason.choices)
    details = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    raised_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="flags_raised"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="flags_resolved",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.TextField(blank=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.device.serial_number} - {self.get_reason_display()}"

    def resolve(self, user, note=""):
        self.is_active = False
        self.resolved_by = user
        self.resolved_at = timezone.now()
        self.resolution_note = note
        self.save(update_fields=["is_active", "resolved_by", "resolved_at", "resolution_note"])


class OwnershipTransfer(models.Model):
    """Audit record of a device changing hands between students."""

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="transfers")
    from_student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transfers_out",
    )
    to_student = models.ForeignKey(
        "students.Student", on_delete=models.CASCADE, related_name="transfers_in"
    )
    reason = models.TextField(blank=True)
    transferred_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.device.serial_number}: {self.from_student} → {self.to_student}"


class TemporaryPermit(models.Model):
    """Written permission for somebody other than the owner to carry a device.

    Covers the very common case of a student lending a laptop to a classmate,
    or a technician taking equipment out for repair.
    """

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="permits")
    bearer_name = models.CharField(max_length=120)
    bearer_id_number = models.CharField(
        max_length=40, blank=True, help_text="Reg number or national ID of the carrier."
    )
    relationship = models.CharField(max_length=80, blank=True)
    reason = models.TextField(blank=True)
    valid_from = models.DateTimeField(default=timezone.now)
    valid_to = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    issued_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="permits_issued"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-valid_to",)

    def __str__(self):
        return f"{self.bearer_name} → {self.device.serial_number}"

    @property
    def is_valid_now(self):
        now = timezone.now()
        return not self.is_revoked and self.valid_from <= now <= self.valid_to
