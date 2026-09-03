from rest_framework import serializers

from . import rules
from .models import Department, EquipmentType, Gate, Rule


class DepartmentSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)
    equipment_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "code", "faculty", "student_count", "equipment_count")


class GateSerializer(serializers.ModelSerializer):
    scans_today = serializers.IntegerField(read_only=True)

    class Meta:
        model = Gate
        fields = (
            "id",
            "name",
            "code",
            "location",
            "is_active",
            "allows_entry",
            "allows_exit",
            "opens_at",
            "closes_at",
            "contact_phone",
            "notes",
            "created_at",
            "scans_today",
        )
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        """A gate that serves neither direction cannot be worked at.

        Easy to reach by unticking both boxes, and the result is a gate that
        appears in the console and refuses every scan recorded against it,
        with no explanation on the screen that would let a guard work out why.
        """
        instance = self.instance
        entry = attrs.get("allows_entry", getattr(instance, "allows_entry", True))
        exit_ = attrs.get("allows_exit", getattr(instance, "allows_exit", True))
        if not entry and not exit_:
            raise serializers.ValidationError(
                {
                    "allows_entry": "A gate has to handle entries, exits or both. To take it out "
                    "of use, untick 'open and manned' instead."
                }
            )

        opens = attrs.get("opens_at", getattr(instance, "opens_at", None))
        closes = attrs.get("closes_at", getattr(instance, "closes_at", None))
        if bool(opens) != bool(closes):
            raise serializers.ValidationError(
                {
                    "closes_at": "Give both an opening and a closing time, or neither. One on its "
                    "own cannot say when the gate is staffed."
                }
            )
        return attrs


class EquipmentTypeSerializer(serializers.ModelSerializer):
    device_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = EquipmentType
        fields = (
            "id",
            "code",
            "label",
            "description",
            "offered_to_students",
            "is_active",
            "sort_order",
            "device_count",
        )

    def validate_code(self, value):
        code = (value or "").strip().upper().replace(" ", "_")
        if not code:
            raise serializers.ValidationError("Give the type a short code.")
        if not code.replace("_", "").isalnum():
            raise serializers.ValidationError("Use letters, digits and underscores only.")
        return code

    def update(self, instance, validated_data):
        """The code is fixed once anything is filed under it.

        It is written onto every device of that type and into every export
        already taken. Renaming it would silently orphan those records, and
        the label - which is all anyone actually reads - can be changed freely
        instead.
        """
        new_code = validated_data.get("code")
        if new_code and new_code != instance.code and instance.devices_exist():
            raise serializers.ValidationError(
                {
                    "code": "Computers are already registered under this code, so it cannot be "
                    "changed. Edit the label instead, which is what people see."
                }
            )
        return super().update(instance, validated_data)


class RuleSerializer(serializers.Serializer):
    """One policy rule: its declared shape, plus whatever is stored for it.

    Not a ModelSerializer. The registry in campus/rules.py is the authority on
    what may be set and what it means; the table only holds values. Serializing
    the table alone would hand the screen a list of keys with no labels, no
    help text and no bounds.
    """

    key = serializers.CharField(read_only=True)
    value = serializers.JSONField()
    kind = serializers.CharField(read_only=True)
    label = serializers.CharField(read_only=True)
    help = serializers.CharField(read_only=True)
    group = serializers.CharField(read_only=True)
    default = serializers.JSONField(read_only=True)
    minimum = serializers.IntegerField(read_only=True, allow_null=True)
    maximum = serializers.IntegerField(read_only=True, allow_null=True)
    is_default = serializers.BooleanField(read_only=True)


class RuleUpdateSerializer(serializers.Serializer):
    """A batch of rule changes, all validated before any is written."""

    values = serializers.DictField()

    def validate_values(self, values):
        if not values:
            raise serializers.ValidationError("Nothing to save.")

        cleaned = {}
        errors = {}
        for key, raw in values.items():
            spec = rules.REGISTRY.get(key)
            if not spec:
                errors[key] = "There is no such setting."
                continue
            try:
                cleaned[key] = spec.clean(raw)
            except ValueError as error:
                errors[key] = str(error)
        if errors:
            raise serializers.ValidationError(errors)
        return cleaned

    def save(self, user=None):
        """Written in one transaction, so a half-applied policy is impossible."""
        from django.db import transaction

        with transaction.atomic():
            for key, value in self.validated_data["values"].items():
                Rule.objects.update_or_create(
                    key=key, defaults={"value": value, "updated_by": user}
                )
        rules.invalidate()
        return self.validated_data["values"]
