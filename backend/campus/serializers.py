from rest_framework import serializers

from .models import Department, Gate


class DepartmentSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ("id", "name", "code", "faculty", "student_count")


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
            "notes",
            "created_at",
            "scans_today",
        )
        read_only_fields = ("created_at",)
