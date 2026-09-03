from django.db.models import Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import CanManageRecords
from config.throttles import WriteThrottle

from . import rules
from .models import Department, EquipmentType, Gate, Rule
from .serializers import (
    DepartmentSerializer,
    EquipmentTypeSerializer,
    GateSerializer,
    RuleUpdateSerializer,
)


class DepartmentViewSet(viewsets.ModelViewSet):
    serializer_class = DepartmentSerializer
    permission_classes = (CanManageRecords,)
    throttle_classes = (WriteThrottle,)
    search_fields = ("name", "code", "faculty")
    ordering_fields = ("name", "code")
    pagination_class = None

    def get_queryset(self):
        return Department.objects.annotate(
            student_count=Count("students", distinct=True),
            equipment_count=Count("equipment", distinct=True),
        )


class GateViewSet(viewsets.ModelViewSet):
    """Gates are the registration office's to open and close.

    Not an administrator setting: a new service entrance is a fact about the
    campus, and the office that keeps the register hears about it first.
    """

    serializer_class = GateSerializer
    permission_classes = (CanManageRecords,)
    throttle_classes = (WriteThrottle,)
    filterset_fields = ("is_active",)
    search_fields = ("name", "code", "location")
    ordering_fields = ("name", "code")
    pagination_class = None

    def get_queryset(self):
        today = timezone.localdate()
        return Gate.objects.annotate(
            scans_today=Count("scan_events", filter=Q(scan_events__created_at__date=today))
        )

    def perform_destroy(self, instance):
        """Closed rather than deleted, when anything was ever recorded there.

        Deleting a gate would set `gate` to null on every scan taken at it, so
        a year of history would quietly stop saying where it happened.
        """
        if instance.scan_events.exists():
            instance.is_active = False
            instance.save(update_fields=["is_active"])
            return
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        gate = self.get_object()
        had_history = gate.scan_events.exists()
        self.perform_destroy(gate)
        return Response(
            {
                "detail": (
                    f"{gate.name} has been closed. Its scan history is kept."
                    if had_history
                    else f"{gate.name} has been removed."
                ),
                "closed_instead_of_deleted": had_history,
            }
        )


class EquipmentTypeViewSet(viewsets.ModelViewSet):
    """What kinds of equipment the register recognises."""

    serializer_class = EquipmentTypeSerializer
    permission_classes = (CanManageRecords,)
    throttle_classes = (WriteThrottle,)
    filterset_fields = ("is_active", "offered_to_students")
    ordering_fields = ("sort_order", "label", "code")
    pagination_class = None

    def get_queryset(self):
        """Types, each with how many computers are filed under it.

        A correlated subquery rather than a join, because `device_type` holds
        a code and not a foreign key - see campus/equipment.py for why. The
        count is what tells a registrar whether retiring a type is harmless or
        would strand two hundred laptops.
        """
        from devices.models import Device

        counted = (
            Device.objects.filter(device_type=OuterRef("code"))
            .order_by()
            .values("device_type")
            .annotate(total=Count("id"))
            .values("total")
        )
        return EquipmentType.objects.annotate(
            device_count=Coalesce(
                Subquery(counted, output_field=IntegerField()), Value(0)
            )
        )

    def destroy(self, request, *args, **kwargs):
        """Retired rather than deleted once anything uses it."""
        row = self.get_object()
        if row.devices_exist():
            row.is_active = False
            row.save(update_fields=["is_active"])
            return Response(
                {
                    "detail": (
                        f"{row.label} is now retired. Computers already registered as this type "
                        f"keep it, and it is no longer offered on new registrations."
                    ),
                    "retired_instead_of_deleted": True,
                }
            )
        row.delete()
        return Response({"detail": f"{row.label} removed.", "retired_instead_of_deleted": False})


class RulesView(APIView):
    """The policy a registration officer sets, without a deployment.

    GET  returns every rule with its label, help text, bounds and current
         value, grouped for display.
    POST takes a partial map of key to value, validates all of it, and writes
         it in one transaction.
    """

    permission_classes = (CanManageRecords,)
    throttle_classes = (WriteThrottle,)

    def get(self, request):
        current = rules.all_rules()
        stored = set(Rule.objects.values_list("key", flat=True))
        return Response(
            {
                "groups": [
                    {"key": key, **meta} for key, meta in rules.GROUPS.items()
                ],
                "rules": [
                    {
                        **spec.as_dict(),
                        "value": current[key],
                        # Lets the screen show which settings this university
                        # has actually decided on, as against which are simply
                        # sitting at whatever shipped.
                        "is_default": key not in stored,
                    }
                    for key, spec in rules.REGISTRY.items()
                ],
            }
        )

    def post(self, request):
        serializer = RuleUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        saved = serializer.save(user=request.user)
        return Response(
            {
                "detail": (
                    f"{len(saved)} setting{'s' if len(saved) != 1 else ''} saved. "
                    "It takes effect at every gate immediately."
                ),
                "values": saved,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """Put one rule back to what it shipped as."""
        key = request.data.get("key")
        if key not in rules.REGISTRY:
            return Response(
                {"key": ["There is no such setting."]}, status=status.HTTP_400_BAD_REQUEST
            )
        Rule.objects.filter(key=key).delete()
        rules.invalidate()
        return Response(
            {
                "detail": f"'{rules.REGISTRY[key].label}' is back to its default.",
                "value": rules.rule(key),
            }
        )
