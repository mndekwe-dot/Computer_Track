from rest_framework import serializers

from .models import Student, normalise_reg_number


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True)
    device_count = serializers.IntegerField(read_only=True)
    is_clear_to_pass = serializers.BooleanField(read_only=True)

    class Meta:
        model = Student
        fields = (
            "id",
            "reg_number",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "national_id",
            "department",
            "department_name",
            "programme",
            "year_of_study",
            "photo",
            "status",
            "status_display",
            "is_clear_to_pass",
            "notes",
            "device_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")

    def validate_reg_number(self, value):
        key = normalise_reg_number(value)
        if not key:
            raise serializers.ValidationError("Registration number is required.")
        clash = Student.objects.filter(reg_number_key=key)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError(
                "Another student already uses this registration number."
            )
        return value.strip().upper()


class StudentBriefSerializer(serializers.ModelSerializer):
    """Compact shape embedded inside device and scan payloads."""

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = ("id", "reg_number", "full_name", "photo", "status", "programme")
