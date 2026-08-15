from django.db.models import Count, Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import audit
from accounts.throttles import LookupBurstThrottle, LookupDailyThrottle
from devices.models import Device
from students.models import Student

from .indexer import filter_devices, filter_students

# A typeahead exists to be scanned by eye while typing. More than this is
# slower to read than to retype.
LIMIT = 8


class SuggestView(APIView):
    """GET /api/search/suggest/?q= - live results while the user types.

    Served entirely off the inverted index: prefix scans return the matching
    ids, then one query per entity type fetches just those rows.
    """

    permission_classes = (IsAuthenticated,)
    # A typeahead fires far more often than a committed lookup, and it reads
    # the same records, so it carries the same per-account ceilings.
    throttle_classes = (LookupBurstThrottle, LookupDailyThrottle)

    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        kinds = (request.query_params.get("kinds") or "students,devices").split(",")

        if len(query) < 2:
            return Response({"query": query, "students": [], "devices": [], "truncated": False})

        payload = {"query": query, "students": [], "devices": []}
        truncated = False

        if "students" in kinds:
            # Sliced straight in SQL - the database applies the limit and
            # stops, instead of shipping every match back to be discarded.
            matches = filter_students(
                Student.objects.select_related("department").annotate(
                    device_count=Count("devices", filter=Q(devices__is_archived=False))
                ),
                query,
            ).order_by("last_name", "first_name")
            rows = list(matches[: LIMIT + 1])
            truncated = truncated or len(rows) > LIMIT
            rows = rows[:LIMIT]
            payload["students"] = [
                {
                    "id": student.id,
                    "reg_number": student.reg_number,
                    "full_name": student.full_name,
                    "status": student.status,
                    "programme": student.programme,
                    "device_count": student.device_count,
                }
                for student in rows
            ]

        if "devices" in kinds:
            matches = filter_devices(
                Device.objects.filter(is_archived=False).select_related("owner"), query
            ).order_by("-registered_at")
            rows = list(matches[: LIMIT + 1])
            truncated = truncated or len(rows) > LIMIT
            rows = rows[:LIMIT]
            payload["devices"] = [
                {
                    "id": device.id,
                    "serial_number": device.serial_number,
                    "label": device.label,
                    "status": device.status,
                    "asset_tag": device.asset_tag,
                    "owner_name": device.owner.full_name if device.owner_id else "",
                    "owner_reg_number": device.owner.reg_number if device.owner_id else "",
                }
                for device in rows
            ]

        payload["truncated"] = truncated
        audit.record(
            request,
            audit.AuditAction.SUGGEST,
            query=query,
            result_count=len(payload["students"]) + len(payload["devices"]),
        )
        return Response(payload)
