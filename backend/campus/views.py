from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets

from accounts.permissions import CanManageRecords

from .models import Department, Gate
from .serializers import DepartmentSerializer, GateSerializer


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = (CanManageRecords,)
    search_fields = ("name", "code", "faculty")
    ordering_fields = ("name", "code")
    pagination_class = None

    def get_queryset(self):
        return Department.objects.annotate(student_count=Count("students"))


class GateViewSet(viewsets.ModelViewSet):
    serializer_class = GateSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("is_active",)
    search_fields = ("name", "code", "location")
    ordering_fields = ("name", "code")
    pagination_class = None

    def get_queryset(self):
        today = timezone.localdate()
        return Gate.objects.annotate(
            scans_today=Count("scan_events", filter=Q(scan_events__created_at__date=today))
        )
