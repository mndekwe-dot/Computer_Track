from rest_framework import serializers

from campus.models import Gate
from campus.rules import rule
from devices.models import Device
from devices.serializers import DeviceGateSerializer

from .models import Direction, LookupMethod, ScanEvent, Verdict


class PreloadedRelatedField(serializers.PrimaryKeyRelatedField):
    """A related field that will take its object from a batch already fetched.

    DRF resolves each primary key with its own `.get()`. That is right for a
    single record and wrong for a queue flush: fifty scans meant fifty device
    lookups, fifty gate lookups, and - because validation asks whether each
    device is blocked - fifty more for flags and owners.

    When the parent has preloaded a map into the context, this reads from it.
    Otherwise it behaves exactly as before, so a single scan is unaffected.
    """

    context_key = None

    def to_internal_value(self, data):
        preloaded = (self.context or {}).get(self.context_key)
        if preloaded is None:
            return super().to_internal_value(data)
        try:
            return preloaded[int(data)]
        except (KeyError, TypeError, ValueError):
            self.fail("does_not_exist", pk_value=data)


class PreloadedDeviceField(PreloadedRelatedField):
    context_key = "preloaded_devices"


class PreloadedGateField(PreloadedRelatedField):
    context_key = "preloaded_gates"


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
    # Resolved from the batch the bulk endpoint preloads, when there is one.
    # Falls back to an ordinary lookup for a single scan.
    device = PreloadedDeviceField(
        queryset=Device.objects.all(), required=False, allow_null=True
    )
    gate = PreloadedGateField(queryset=Gate.objects.all(), required=False, allow_null=True)

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
        # lecturer vouching - but the reason has to be on the record. How much
        # of a reason counts is the registration office's call: long enough
        # that "ok" does not pass, short enough not to be an obstacle at a
        # busy gate.
        if device and verdict == Verdict.OVERRIDE and rule("gate.require_override_reason"):
            written = (attrs.get("override_reason") or "").strip()
            minimum = rule("gate.override_reason_min_length")
            if not written:
                raise serializers.ValidationError(
                    {"override_reason": "Explain why this blocked device was allowed through."}
                )
            if len(written) < minimum:
                raise serializers.ValidationError(
                    {
                        "override_reason": (
                            f"Give a fuller reason - at least {minimum} characters. This is the "
                            f"only record of why a held computer was let through."
                        )
                    }
                )

        # A gate that does not serve this direction cannot have seen this
        # movement. Recorded against the wrong gate, the log stops answering
        # the question it exists for: which way did it go, and past whom.
        gate = attrs.get("gate")
        direction = attrs.get("direction")
        if gate and direction and not gate.allows(direction):
            way = "entries" if direction == Direction.IN else "exits"
            raise serializers.ValidationError(
                {"gate": f"{gate.name} does not handle {way}. Choose the gate this happened at."}
            )
        if device and verdict == Verdict.ALLOWED and device.is_blocked:
            raise serializers.ValidationError(
                {
                    "verdict": "This device is blocked. Record DENIED, or use OVERRIDE "
                    "with a written reason."
                }
            )

        # University property needs a gate pass to leave, and only to leave:
        # the same projector coming back in must not be stopped for want of
        # one. Enforced here rather than in the console, because the console
        # is a client and the offline queue lives in localStorage.
        if (
            device
            and verdict == Verdict.ALLOWED
            and attrs.get("direction") == Direction.OUT
            and device.exit_restrictions()
        ):
            raise serializers.ValidationError(
                {
                    "verdict": "This is university property with no valid gate pass. "
                    "Issue a permit, record DENIED, or use OVERRIDE with a written reason."
                }
            )

        # A permit cited at the gate has to actually be in force, and has to
        # belong to this computer. Without the second check a guard could
        # attach any valid permit to any device and the log would look clean.
        permit = attrs.get("permit")
        if permit:
            if device and permit.device_id != device.pk:
                raise serializers.ValidationError(
                    {"permit": "That gate pass was issued for a different computer."}
                )
            if not permit.is_valid_now:
                raise serializers.ValidationError(
                    {"permit": "That gate pass has expired or been revoked."}
                )

        if device and not attrs.get("student"):
            attrs["student"] = device.owner

        # `claimed_serial` and `claimed_reg_number` stay as the guard typed
        # them: they are the claim, and a mistyped one is evidence too. But
        # `device_label` and `student_name` are snapshots of the register at
        # decision time, so they are taken from the record rather than from
        # whatever the client sent. Trusting the client for those let a
        # tampered request write a history that never happened, and put
        # attacker-chosen text into the administrator's CSV export.
        if device:
            # The serial is part of the snapshot on purpose. It has to stay
            # readable after the device row is gone, and `claimed_serial` only
            # holds one when the guard happened to search by serial rather
            # than by registration number.
            attrs["device_label"] = f"{device.label} · {device.serial_number}"
        if attrs.get("student"):
            attrs["student_name"] = attrs["student"].full_name
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
        # `direction` comes from the console's Entering/Leaving toggle. Absent,
        # assume the equipment is leaving: that is the direction the checks
        # exist for, and the safer assumption of the two.
        if self.context.get("direction", Direction.OUT) == Direction.OUT:
            reasons = reasons + obj.exit_restrictions()
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
    """Flush the browser's offline queue in one request.

    A gate that has been offline for an hour arrives with a hundred scans, so
    this is the one endpoint where per-item query cost actually compounds.
    Everything the batch refers to is fetched up front, in the same shape the
    gate console uses, and the child serializers read from that.
    """

    scans = ScanEventCreateSerializer(many=True)

    def to_internal_value(self, data):
        self._preload(data)
        return super().to_internal_value(data)

    def _preload(self, data):
        from campus.models import Gate
        from devices import queries

        rows = [row for row in (data.get("scans") or []) if isinstance(row, dict)]
        device_ids = _as_ids(row.get("device") for row in rows)
        gate_ids = _as_ids(row.get("gate") for row in rows)

        # `for_gate` because validation asks each device whether it is blocked
        # and whether it may leave, which reads flags, permits and the owner.
        self._context["preloaded_devices"] = {
            device.pk: device for device in queries.for_gate().filter(pk__in=device_ids)
        }
        self._context["preloaded_gates"] = {
            gate.pk: gate for gate in Gate.objects.filter(pk__in=gate_ids)
        }


def _as_ids(values):
    ids = set()
    for value in values:
        try:
            ids.add(int(value))
        except (TypeError, ValueError):
            # Not a usable id. Left out here so the field reports it in the
            # ordinary way rather than this helper inventing an error.
            continue
    return ids
