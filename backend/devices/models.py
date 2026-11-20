import re
import uuid

from django.db import models
from django.utils import timezone

from campus import equipment
from campus.rules import rule, text as rule_text


def normalise_serial(value):
    """Serials get read off tiny stickers - ignore spacing and case."""
    return re.sub(r"[\s\-]", "", (value or "")).upper()


# The codes a fresh database is seeded with, kept as names so the rest of the
# code can refer to LAPTOP without a string literal. This is *not* the list of
# valid types any more: that is a table the registration office owns, in
# campus.EquipmentType. Nothing here validates anything.
class DeviceType:
    LAPTOP = "LAPTOP"
    TABLET = "TABLET"
    DESKTOP = "DESKTOP"
    MONITOR = "MONITOR"
    PROJECTOR = "PROJECTOR"
    OTHER = "OTHER"


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
    # No `choices`: the valid list is campus.EquipmentType, which a registrar
    # edits. Validated in the serializers against the active rows there.
    device_type = models.CharField(max_length=30, default=DeviceType.LAPTOP, db_index=True)
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
    # Where and when it was bought, when the registration office asks for it
    # (registration.require_ownership_proof). Not proof of anything by itself:
    # its value is that somebody registering a computer they picked up an hour
    # ago has to invent an answer, and the answer is on the record when the
    # real owner reports it missing.
    purchase_details = models.CharField(
        max_length=200,
        blank=True,
        help_text="Where and roughly when this was bought, as the owner describes it.",
    )
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
    def device_type_label(self):
        return equipment.label_for(self.device_type)

    @property
    def label(self):
        parts = [self.brand, self.model_name]
        return " ".join(p for p in parts if p) or self.device_type_label

    def _prefetched(self, name):
        """The prefetched rows for a relation, or None if it was not prefetched.

        This is the difference between one query and one query per device.
        `self.flags.filter(is_active=True)` reads correctly and looks harmless,
        but calling `.filter()` on a related manager always goes back to the
        database - it cannot use `prefetch_related`, which caches the result of
        `.all()` and nothing else. A device list rendering blocking reasons for
        fifty rows therefore issued fifty extra queries, and the gate console
        does exactly that on every lookup.
        """
        return getattr(self, "_prefetched_objects_cache", {}).get(name)

    @property
    def active_flags(self):
        cached = self._prefetched("flags")
        if cached is not None:
            return [flag for flag in cached if flag.is_active]
        return list(self.flags.filter(is_active=True))

    def valid_permits(self):
        """Permits in force right now, as a list.

        Was a queryset. Callers only ever iterated it or asked whether it was
        empty, and returning a list lets the prefetched rows be reused.
        """
        cached = self._prefetched("permits")
        if cached is not None:
            return [permit for permit in cached if permit.is_valid_now]
        now = timezone.now()
        return list(self.permits.filter(is_revoked=False, valid_from__lte=now, valid_to__gte=now))

    def blocking_reasons(self):
        """Everything that should stop this device leaving, in plain language.

        Returned as a list so the console can show every problem at once
        instead of the guard discovering them one at a time. Both the wording
        and whether each check applies at all are rules the registration
        office owns; see campus/rules.py.
        """
        reasons = []
        if self.status == DeviceStatus.STOLEN:
            reasons.append(rule_text("gate.message_stolen"))
        elif self.status == DeviceStatus.LOST:
            reasons.append(rule_text("gate.message_lost"))
        elif self.status == DeviceStatus.PENDING and rule("gate.block_pending"):
            reasons.append(rule_text("gate.message_pending"))
        elif self.status == DeviceStatus.RETIRED:
            reasons.append(rule_text("gate.message_retired"))
        for flag in self.active_flags:
            reasons.append(f"{flag.get_reason_display()}: {flag.details or 'no details given'}")
        if (
            self.owner
            and not self.owner.is_clear_to_pass
            and rule("gate.block_suspended_owner")
        ):
            reasons.append(
                rule_text("gate.message_owner_inactive", status=self.owner.get_status_display())
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
        if not rule("gate.university_property_needs_pass"):
            return []
        if self.valid_permits():
            return []
        return [rule_text("gate.message_needs_pass")]

    @property
    def is_blocked(self):
        return bool(self.blocking_reasons())


class ApprovalEvidence(models.Model):
    """What the registration officer checked before approving a registration.

    No system can prove who legally owns a laptop. What it can do is record,
    at the one moment the computer and its claimed owner are in the same room
    as an officer, exactly what was checked. When the real owner later
    reports it stolen, this is what shows whether the approval was careful.

    Written once, at approval, and never edited: evidence that can be changed
    afterwards is not evidence.
    """

    device = models.OneToOneField(
        Device, on_delete=models.CASCADE, related_name="approval_evidence"
    )
    identity_checked = models.BooleanField(
        default=False, help_text="Student ID card matched the owner on the record."
    )
    device_unlocked = models.BooleanField(
        default=False, help_text="Owner unlocked the computer in front of the officer."
    )
    serial_matches = models.BooleanField(
        default=False,
        help_text="Serial read from the running system matches the one submitted.",
    )
    proof_of_purchase_seen = models.BooleanField(
        default=False, help_text="A receipt, invoice or loan agreement was shown."
    )
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approval_evidence_recorded",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evidence for {self.device}"

    @property
    def checks_passed(self):
        return sum(
            (
                self.identity_checked,
                self.device_unlocked,
                self.serial_matches,
                self.proof_of_purchase_seen,
            )
        )


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


class AttemptOutcome(models.TextChoices):
    """Why a public registration attempt is on the record."""

    DUPLICATE_SERIAL = "DUPLICATE_SERIAL", "Serial already on the register"
    MATCHED_MISSING = "MATCHED_MISSING", "Serial matches a computer reported missing"
    LIMIT_REACHED = "LIMIT_REACHED", "Student is at their registration limit"
    TOO_MANY_ATTEMPTS = "TOO_MANY_ATTEMPTS", "Repeated submissions in a short window"
    VERIFY_FAILED = "VERIFY_FAILED", "Identity check failed"
    ACCEPTED = "ACCEPTED", "Accepted for approval"


class RegistrationAttempt(models.Model):
    """Every submission to the public form, including the refused ones.

    The refusals are the point. A student registering their own laptop
    succeeds once and is never seen here again. What this table catches is the
    shape of somebody working through a bag: a run of different serials from
    one registration number, or one serial tried against several.

    Before this existed, a refused submission returned an error message and
    left no trace at all - so the single most informative event the public
    form can produce was the one thing it did not record.

    It deliberately holds no photograph and no description, only what is
    needed to see a pattern and find the submission it refers to.
    """

    reg_number = models.CharField(max_length=40, blank=True, help_text="Exactly as submitted.")
    student = models.ForeignKey(
        "students.Student",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registration_attempts",
    )
    serial_number = models.CharField(max_length=80, blank=True)
    serial_key = models.CharField(max_length=80, blank=True, db_index=True)
    brand = models.CharField(max_length=60, blank=True)
    outcome = models.CharField(max_length=30, choices=AttemptOutcome.choices, db_index=True)
    detail = models.CharField(max_length=300, blank=True)
    # The device this collided with, when it collided with one. Kept so an
    # officer reviewing the attempt can open the record without searching.
    existing_device = models.ForeignKey(
        Device,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="registration_collisions",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="attempts_reviewed",
    )
    review_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["outcome", "-created_at"], name="attempt_outcome_idx"),
            models.Index(fields=["reg_number", "-created_at"], name="attempt_reg_idx"),
        ]

    def __str__(self):
        return f"{self.reg_number} {self.serial_number} {self.outcome}"

    @property
    def needs_review(self):
        """Worth an officer's time, as distinct from merely being recorded.

        An accepted registration and a mistyped serial are noise. A serial
        that matches a computer somebody has reported stolen is not.
        """
        return self.outcome in {
            AttemptOutcome.MATCHED_MISSING,
            AttemptOutcome.TOO_MANY_ATTEMPTS,
            AttemptOutcome.LIMIT_REACHED,
        }
