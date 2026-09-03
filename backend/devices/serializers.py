from django.utils import timezone
from rest_framework import serializers

from campus import equipment
from config.media import SignedImageField
from students.models import Student
from students.serializers import StudentBriefSerializer

from .models import (
    AttemptOutcome,
    Device,
    DeviceFlag,
    Ownership,
    OwnershipTransfer,
    RegistrationAttempt,
    TemporaryPermit,
    normalise_serial,
)


class DeviceFlagSerializer(serializers.ModelSerializer):
    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    raised_by_name = serializers.CharField(source="raised_by.get_full_name", read_only=True)
    device_serial = serializers.CharField(source="device.serial_number", read_only=True)
    owner_reg_number = serializers.CharField(
        source="device.owner.reg_number", read_only=True, allow_null=True, default=None
    )
    owner_name = serializers.CharField(
        source="device.owner.full_name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = DeviceFlag
        fields = (
            "id",
            "device",
            "device_serial",
            "owner_reg_number",
            "owner_name",
            "reason",
            "reason_display",
            "details",
            "is_active",
            "raised_by",
            "raised_by_name",
            "created_at",
            "resolved_by",
            "resolved_at",
            "resolution_note",
        )
        read_only_fields = ("raised_by", "created_at", "resolved_by", "resolved_at", "is_active")


class TemporaryPermitSerializer(serializers.ModelSerializer):
    is_valid_now = serializers.BooleanField(read_only=True)
    device_serial = serializers.CharField(source="device.serial_number", read_only=True)
    owner_name = serializers.CharField(
        source="device.owner.full_name", read_only=True, allow_null=True, default=None
    )
    issued_by_name = serializers.CharField(source="issued_by.get_full_name", read_only=True)

    class Meta:
        model = TemporaryPermit
        fields = (
            "id",
            "device",
            "device_serial",
            "owner_name",
            "bearer_name",
            "bearer_id_number",
            "relationship",
            "reason",
            "valid_from",
            "valid_to",
            "is_revoked",
            "is_valid_now",
            "issued_by",
            "issued_by_name",
            "created_at",
        )
        read_only_fields = ("issued_by", "created_at")

    def validate(self, attrs):
        valid_from = attrs.get("valid_from") or getattr(self.instance, "valid_from", timezone.now())
        valid_to = attrs.get("valid_to") or getattr(self.instance, "valid_to", None)
        if valid_to and valid_to <= valid_from:
            raise serializers.ValidationError(
                {"valid_to": "The permit must expire after it starts."}
            )
        return attrs


class OwnershipTransferSerializer(serializers.ModelSerializer):
    from_student_detail = StudentBriefSerializer(source="from_student", read_only=True)
    to_student_detail = StudentBriefSerializer(source="to_student", read_only=True)
    transferred_by_name = serializers.CharField(
        source="transferred_by.get_full_name", read_only=True
    )

    class Meta:
        model = OwnershipTransfer
        fields = (
            "id",
            "device",
            "from_student",
            "from_student_detail",
            "to_student",
            "to_student_detail",
            "reason",
            "transferred_by",
            "transferred_by_name",
            "created_at",
        )
        read_only_fields = ("transferred_by", "created_at", "from_student")


class DeviceSerializer(serializers.ModelSerializer):
    owner_detail = StudentBriefSerializer(source="owner", read_only=True)
    label = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    device_type_display = serializers.CharField(source="device_type_label", read_only=True)
    registered_by_name = serializers.CharField(
        source="registered_by.get_full_name", read_only=True
    )
    is_blocked = serializers.BooleanField(read_only=True)
    blocking_reasons = serializers.SerializerMethodField()
    active_flag_count = serializers.SerializerMethodField()
    photo = SignedImageField(required=False, allow_null=True)
    ownership_display = serializers.CharField(source="get_ownership_display", read_only=True)
    # No auto uniqueness validator: `validate_serial_number` below checks the
    # normalised key, which catches spacing and case differences the field's
    # own exact-match check would let through, and says who holds it.
    serial_number = serializers.CharField(validators=[])
    department_name = serializers.CharField(
        source="department.name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = Device
        fields = (
            "id",
            "uid",
            "serial_number",
            "asset_tag",
            "device_type",
            "device_type_display",
            "brand",
            "model_name",
            "label",
            "colour",
            "distinguishing_marks",
            "ownership",
            "ownership_display",
            "owner",
            "owner_detail",
            "department",
            "department_name",
            "custodian_name",
            "photo",
            "status",
            "status_display",
            "is_archived",
            "notes",
            "registered_by",
            "registered_by_name",
            "registered_at",
            "updated_at",
            "is_blocked",
            "blocking_reasons",
            "active_flag_count",
        )
        read_only_fields = ("uid", "registered_by", "registered_at", "updated_at")

    def get_blocking_reasons(self, obj):
        return obj.blocking_reasons()

    def get_exit_restrictions(self, obj):
        return obj.exit_restrictions()

    def validate(self, attrs):
        """Each kind of ownership needs a different thing filled in.

        A student laptop without an owner is unattributable, and university
        property without a department or a custodian gives a guard nobody to
        call when it turns up at a gate at night.
        """
        instance = self.instance
        ownership = attrs.get("ownership", getattr(instance, "ownership", Ownership.STUDENT))
        owner = attrs.get("owner", getattr(instance, "owner", None))
        department = attrs.get("department", getattr(instance, "department", None))
        custodian = attrs.get("custodian_name", getattr(instance, "custodian_name", "")) or ""

        if ownership == Ownership.STUDENT and not owner:
            raise serializers.ValidationError(
                {"owner": "Choose the student this computer belongs to."}
            )
        if ownership == Ownership.UNIVERSITY:
            if owner:
                raise serializers.ValidationError(
                    {"owner": "University property belongs to a department, not to a student."}
                )
            if not department and not custodian.strip():
                raise serializers.ValidationError(
                    {
                        "department": "Give the department that owns this, or the member of "
                        "staff answerable for it."
                    }
                )
        return attrs

    def get_active_flag_count(self, obj):
        # `len` of the prefetch-aware list, not `.count()`: a COUNT query per
        # row is exactly the N+1 that property exists to avoid.
        return len(obj.active_flags)

    def validate_device_type(self, value):
        """Checked against the table the registration office keeps."""
        if not equipment.is_valid(value):
            raise serializers.ValidationError(
                "Choose a type of equipment that is on the register. If the right one is "
                "missing, add it under Equipment Types."
            )
        return value

    def validate_serial_number(self, value):
        key = normalise_serial(value)
        if not key:
            raise serializers.ValidationError("Serial number is required.")
        clash = Device.objects.filter(serial_key=key)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            existing = clash.first()
            if existing.owner:
                raise serializers.ValidationError(
                    f"This serial is already registered to {existing.owner.reg_number} "
                    f"({existing.owner.full_name})."
                )
            raise serializers.ValidationError(
                "This serial is already registered as university property"
                + (f" to {existing.department.name}." if existing.department else ".")
            )
        return value.strip().upper()


class DeviceGateSerializer(DeviceSerializer):
    """Device shape used at the gate: adds the live permits the guard needs."""

    valid_permits = serializers.SerializerMethodField()
    exit_restrictions = serializers.SerializerMethodField()
    active_flags = DeviceFlagSerializer(many=True, read_only=True)
    last_movement = serializers.SerializerMethodField()
    owner_photo = SignedImageField(
        source="owner.photo", read_only=True, allow_null=True, default=None
    )

    class Meta(DeviceSerializer.Meta):
        fields = DeviceSerializer.Meta.fields + (
            "valid_permits",
            "exit_restrictions",
            "active_flags",
            "last_movement",
            "owner_photo",
        )

    def get_valid_permits(self, obj):
        return TemporaryPermitSerializer(obj.valid_permits(), many=True).data

    def get_last_movement(self, obj):
        """The most recent scan.

        `obj.scan_events.order_by(...).first()` is one query per device, which
        on a gate lookup showing a student's four computers is four queries for
        four values. `devices.queries.with_last_movement` annotates them onto
        the row instead; the fallback below is for callers that serialize a
        device they built by hand.
        """
        if hasattr(obj, "last_scan_at"):
            if not obj.last_scan_at:
                return None
            return {
                "direction": obj.last_scan_direction,
                "verdict": obj.last_scan_verdict,
                "gate": obj.last_scan_gate,
                "created_at": obj.last_scan_at,
            }

        last = obj.scan_events.order_by("-created_at").first()
        if not last:
            return None
        return {
            "direction": last.direction,
            "verdict": last.verdict,
            "gate": last.gate.name if last.gate else None,
            "created_at": last.created_at,
        }


class DeviceTransferSerializer(serializers.Serializer):
    """Input for POST /devices/{id}/transfer/ - move a device to a new owner."""

    to_student_reg_number = serializers.CharField()
    reason = serializers.CharField(allow_blank=True, required=False)

    def validate_to_student_reg_number(self, value):
        from students.models import normalise_reg_number

        student = Student.objects.filter(reg_number_key=normalise_reg_number(value)).first()
        if not student:
            raise serializers.ValidationError("No student found with that registration number.")
        return student


class RegistrationAttemptSerializer(serializers.ModelSerializer):
    """A public-form submission, as an officer reviews it."""

    outcome_display = serializers.CharField(source="get_outcome_display", read_only=True)
    student_name = serializers.CharField(
        source="student.full_name", read_only=True, allow_null=True, default=None
    )
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.get_full_name", read_only=True, allow_null=True, default=None
    )
    existing_device_serial = serializers.CharField(
        source="existing_device.serial_number", read_only=True, allow_null=True, default=None
    )
    existing_device_status = serializers.CharField(
        source="existing_device.status", read_only=True, allow_null=True, default=None
    )
    needs_review = serializers.BooleanField(read_only=True)

    class Meta:
        model = RegistrationAttempt
        fields = (
            "id",
            "reg_number",
            "student",
            "student_name",
            "serial_number",
            "brand",
            "outcome",
            "outcome_display",
            "detail",
            "existing_device",
            "existing_device_serial",
            "existing_device_status",
            "needs_review",
            "ip_address",
            "reviewed_at",
            "reviewed_by",
            "reviewed_by_name",
            "review_note",
            "created_at",
        )
        read_only_fields = fields
