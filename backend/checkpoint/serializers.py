from rest_framework import serializers

from devices.models import Device
from devices.serializers import DeviceGateSerializer

from .models import Direction, LookupMethod, ScanEvent, Verdict


class ScanEventSerializer(serializers.ModelSerializer):
    guard_name = serializers.SerializerMethodField()
    gate_name = serializers.CharField(source="gate.name", read_only=True)
    direction_display = serializers.CharField(source="get_direction_display", read_only=True)
    verdict_display = serializers.CharField(source="get_verdict_display", read_only=True)
    happened_at = serializers.DateTimeField(read_only=True)
    owner_reg_number = serializers.CharField(source="student.reg_number", read_only=True)

    class Meta:
        model = ScanEvent
        fields = (
            "id",
            "device",
            "student",
            "owner_reg_number",
            "gate",
            "gate_name",
            "guard",
            "guard_name",
            "direction",
            "direction_display",
            "verdict",
            "verdict_display",
            "method",
            "claimed_serial",
            "claimed_reg_number",
            "device_label",
            "student_name",
            "permit",
            "bearer_name",
            "override_reason",
            "notes",
            "client_reference",
            "client_timestamp",
            "happened_at",
            "created_at",
        )
        read_only_fields = ("guard", "created_at")

    def get_guard_name(self, obj):
        if not obj.guard:
            return ""
        return obj.guard.get_full_name() or obj.guard.username


class ScanEventCreateSerializer(ScanEventSerializer):
    # The model's unique constraint would make a replayed offline scan fail
    # validation with a 400. Dropping the auto-generated UniqueValidator lets
    # create() below answer with the original scan instead, which is what an
    # idempotency key is for.
    client_reference = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True, validators=[]
    )

    def validate_client_reference(self, value):
        # Empty strings would collide with each other on the unique index;
        # "no reference" has to be NULL.
        return (value or "").strip() or None

    def validate(self, attrs):
        device = attrs.get("device")
        verdict = attrs.get("verdict")

        if verdict != Verdict.UNREGISTERED and not device:
            raise serializers.ValidationError(
                {"device": "Select the device, or record the scan as UNREGISTERED."}
            )

        # A guard may wave a blocked device through - an ambulance case, a
        # lecturer vouching - but the reason has to be on the record.
        if device and verdict == Verdict.OVERRIDE and not attrs.get("override_reason", "").strip():
            raise serializers.ValidationError(
                {"override_reason": "Explain why this blocked device was allowed through."}
            )
        if device and verdict == Verdict.ALLOWED and device.is_blocked:
            raise serializers.ValidationError(
                {
                    "verdict": "This device is blocked. Record DENIED, or use OVERRIDE "
                    "with a written reason."
                }
            )

        if device and not attrs.get("student"):
            attrs["student"] = device.owner
        return attrs

    def create(self, validated_data):
        # An offline queue may replay the same scan; return the original
        # instead of writing a duplicate row.
        reference = validated_data.get("client_reference")
        if reference:
            existing = ScanEvent.objects.filter(client_reference=reference).first()
            if existing:
                return existing
        return super().create(validated_data)


class GateLookupDeviceSerializer(DeviceGateSerializer):
    """Device as the guard sees it, with a clear pass/hold recommendation."""

    recommendation = serializers.SerializerMethodField()

    class Meta(DeviceGateSerializer.Meta):
        fields = DeviceGateSerializer.Meta.fields + ("recommendation",)

    def get_recommendation(self, obj):
        reasons = obj.blocking_reasons()
        if reasons:
            return {"action": "HOLD", "reasons": reasons}
        return {"action": "PASS", "reasons": []}


class GateLookupResultSerializer(serializers.Serializer):
    """Read-only envelope returned by the gate lookup endpoint."""

    query = serializers.CharField()
    resolved_as = serializers.ChoiceField(choices=["STUDENT", "DEVICE", "NOT_FOUND"])
    method = serializers.ChoiceField(choices=LookupMethod.choices)
    student = serializers.DictField(allow_null=True)
    devices = serializers.ListField()
    matched_device_id = serializers.IntegerField(allow_null=True)
    warnings = serializers.ListField(child=serializers.CharField())
    message = serializers.CharField(allow_blank=True)


class BulkScanSerializer(serializers.Serializer):
    """Flush the browser's offline queue in one request."""

    scans = ScanEventCreateSerializer(many=True)
