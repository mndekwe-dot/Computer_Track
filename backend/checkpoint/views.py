import csv
import logging
from datetime import timedelta

from django.db.models import Count, Max, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import audit
from config.exports import csv_safe_row
from accounts.throttles import LookupBurstThrottle, LookupDailyThrottle
from campus.models import Gate
from students.serializers import StudentSerializer

from notifications.service import notify_owner_of_exit

from .lookup import resolve_query, suggest
from .models import Direction, ScanEvent, Verdict
from .serializers import (
    BulkScanSerializer,
    GateLookupDeviceSerializer,
    ScanEventCreateSerializer,
    ScanEventSerializer,
)

logger = logging.getLogger(__name__)


class GateLookupView(APIView):
    """The screen the guard stares at all day.

    GET /api/checkpoint/lookup/?q=218001234
    Accepts a reg number, a serial, an asset tag or a scanned QR payload and
    always answers the same question: whose computer is this, and may it pass?
    """

    permission_classes = (IsAuthenticated,)
    # Per-account ceilings: one guard login cannot enumerate the register,
    # whether quickly or slowly.
    throttle_classes = (LookupBurstThrottle, LookupDailyThrottle)

    def get(self, request):
        query = request.query_params.get("q", "")
        # The console's Entering/Leaving toggle. It changes the answer for
        # university property, which may come back in freely but needs a pass
        # to go out, so the lookup has to know which way it is travelling.
        direction = (
            Direction.IN if request.query_params.get("direction") == Direction.IN else Direction.OUT
        )
        resolved_as, student, devices, matched, method = resolve_query(query)

        warnings = []
        if student and not student.is_clear_to_pass:
            warnings.append(
                f"Student record is {student.get_status_display().upper()} - refer to the "
                f"registration office before allowing equipment through."
            )
        if resolved_as == "STUDENT" and not devices:
            warnings.append(
                "This student has no computer registered. Any device they carry must be "
                "registered before it can leave campus."
            )

        payload = {
            "query": query,
            "resolved_as": resolved_as,
            "method": method,
            "student": StudentSerializer(student).data if student else None,
            "devices": GateLookupDeviceSerializer(
                devices, many=True, context={"direction": direction}
            ).data,
            "matched_device_id": matched.id if matched else None,
            "warnings": warnings,
            "message": "",
        }

        if resolved_as == "NOT_FOUND":
            payload["message"] = (
                "No student or device matches that entry. Check the spelling, or record "
                "the item as an unregistered device."
            )
            payload["suggestions"] = suggest(query)

        audit.record(
            request,
            audit.AuditAction.GATE_LOOKUP,
            query=query,
            result_count=len(payload["devices"]),
            subject_reg_number=student.reg_number if student else "",
        )
        return Response(payload)


class ScanEventViewSet(viewsets.ModelViewSet):
    """Append-only: scans can be created and read, never edited or deleted."""

    permission_classes = (IsAuthenticated,)
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ("gate", "guard", "direction", "verdict", "device", "student", "method")
    search_fields = (
        "claimed_serial",
        "claimed_reg_number",
        "device_label",
        "student_name",
        "bearer_name",
    )
    ordering_fields = ("created_at",)

    def get_queryset(self):
        queryset = ScanEvent.objects.select_related("gate", "guard", "device", "student")
        params = self.request.query_params
        date_from, date_to = params.get("date_from"), params.get("date_to")
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        if params.get("problems") in {"1", "true", "True"}:
            queryset = queryset.filter(
                verdict__in=[Verdict.DENIED, Verdict.OVERRIDE, Verdict.UNREGISTERED]
            )
        return queryset

    def get_serializer_class(self):
        return ScanEventCreateSerializer if self.action == "create" else ScanEventSerializer

    def perform_create(self, serializer):
        gate = serializer.validated_data.get("gate") or self.request.user.default_gate
        scan = serializer.save(guard=self.request.user, gate=gate)
        # Queues an outbox row and returns; the actual sending happens off the
        # request path. Swallows its own failures, and is wrapped again here so
        # nothing about notifying can ever fail a recorded scan.
        try:
            notify_owner_of_exit(scan)
        except Exception:
            logger.exception("Exit notification failed for scan %s", scan.pk)

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        """Flush a guard's offline queue. Duplicates are ignored by reference."""
        serializer = BulkScanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        created = []
        for item in serializer.validated_data["scans"]:
            gate = item.get("gate") or request.user.default_gate
            reference = item.get("client_reference")
            if reference and ScanEvent.objects.filter(client_reference=reference).exists():
                continue
            created.append(ScanEvent(**{**item, "guard": request.user, "gate": gate}))
        for scan in created:
            scan.save()
        return Response(
            {"synced": len(created), "scans": ScanEventSerializer(created, many=True).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def export(self, request):
        """CSV of the filtered log - what security hands to an investigation."""
        queryset = self.filter_queryset(self.get_queryset())[:10000]
        # Bulk extraction is the read most worth being able to account for.
        audit.record(
            request,
            audit.AuditAction.EXPORT,
            query=request.query_params.urlencode()[:200],
            result_count=len(queryset),
        )
        response = HttpResponse(content_type="text/csv")
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M")
        response["Content-Disposition"] = f'attachment; filename="gate-log-{stamp}.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Timestamp",
                "Gate",
                "Guard",
                "Direction",
                "Verdict",
                "Method",
                "Reg number",
                "Student",
                "Device",
                "Serial",
                "Carried by",
                "Override reason",
                "Notes",
            ]
        )
        for scan in queryset:
            # Every cell goes through csv_safe_row: a value beginning with `=`
            # is a formula to a spreadsheet, and much of what follows was typed
            # by a student on the public form or a guard at a gate.
            writer.writerow(
                csv_safe_row([
                    timezone.localtime(scan.happened_at).strftime("%Y-%m-%d %H:%M:%S"),
                    scan.gate.name if scan.gate else "",
                    (scan.guard.get_full_name() or scan.guard.username) if scan.guard else "",
                    scan.get_direction_display(),
                    scan.get_verdict_display(),
                    scan.get_method_display(),
                    scan.claimed_reg_number,
                    scan.student_name,
                    scan.device_label,
                    scan.claimed_serial,
                    scan.bearer_name,
                    scan.override_reason,
                    scan.notes,
                ])
            )
        return response


class DashboardView(APIView):
    """Numbers for the security office wall screen."""

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()
        week_ago = today - timedelta(days=6)

        today_scans = ScanEvent.objects.filter(created_at__date=today)
        verdicts = {
            row["verdict"]: row["total"]
            for row in today_scans.values("verdict").annotate(total=Count("id"))
        }

        # A device is "on campus" when its most recent successful scan was an entry.
        latest_ids = (
            ScanEvent.objects.filter(device__isnull=False)
            .values("device")
            .annotate(last_id=Max("id"))
            .values_list("last_id", flat=True)
        )
        on_campus = ScanEvent.objects.filter(
            id__in=list(latest_ids),
            direction=Direction.IN,
            verdict__in=[Verdict.ALLOWED, Verdict.OVERRIDE],
        ).count()

        by_gate = list(
            Gate.objects.filter(is_active=True)
            .annotate(
                scans_today=Count("scan_events", filter=Q(scan_events__created_at__date=today)),
                denials_today=Count(
                    "scan_events",
                    filter=Q(
                        scan_events__created_at__date=today,
                        scan_events__verdict=Verdict.DENIED,
                    ),
                ),
            )
            .values("id", "name", "code", "scans_today", "denials_today")
        )

        # Entries and exits are charted as two series, so they are counted
        # per day here rather than derived in the browser.
        trend_rows = (
            ScanEvent.objects.filter(created_at__date__gte=week_ago)
            .values("created_at__date")
            .annotate(
                total=Count("id"),
                entries=Count("id", filter=Q(direction=Direction.IN)),
                exits=Count("id", filter=Q(direction=Direction.OUT)),
            )
        )
        trend_map = {row["created_at__date"]: row for row in trend_rows}
        trend = []
        for offset in range(7):
            day = week_ago + timedelta(days=offset)
            row = trend_map.get(day)
            trend.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%a"),
                    "total": row["total"] if row else 0,
                    "entries": row["entries"] if row else 0,
                    "exits": row["exits"] if row else 0,
                }
            )

        recent_problems = ScanEvent.objects.filter(
            verdict__in=[Verdict.DENIED, Verdict.OVERRIDE, Verdict.UNREGISTERED]
        ).select_related("gate", "guard")[:10]

        return Response(
            {
                "generated_at": now,
                "today": {
                    "total": today_scans.count(),
                    "entries": today_scans.filter(direction=Direction.IN).count(),
                    "exits": today_scans.filter(direction=Direction.OUT).count(),
                    "allowed": verdicts.get(Verdict.ALLOWED, 0),
                    "denied": verdicts.get(Verdict.DENIED, 0),
                    "overrides": verdicts.get(Verdict.OVERRIDE, 0),
                    "unregistered": verdicts.get(Verdict.UNREGISTERED, 0),
                },
                "devices_on_campus": on_campus,
                "by_gate": by_gate,
                "trend": trend,
                "recent_problems": ScanEventSerializer(recent_problems, many=True).data,
            }
        )
