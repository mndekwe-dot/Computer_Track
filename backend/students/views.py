from django.db.models import Count, Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from accounts import audit
from accounts.permissions import CanManageRecords
from search.indexer import filter_students

from .importer import commit, parse_csv
from .models import Student, StudentStatus, normalise_reg_number
from .serializers import StudentSerializer


class StudentViewSet(viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("status", "department", "year_of_study")
    ordering_fields = ("last_name", "reg_number", "created_at")
    # `search_fields` is deliberately absent: DRF's SearchFilter builds
    # `icontains`, which cannot use an index. Search goes through the inverted
    # index below instead.

    def get_queryset(self):
        queryset = Student.objects.select_related("department").annotate(
            device_count=Count("devices", filter=Q(devices__is_archived=False))
        )

        search = self.request.query_params.get("search")
        if search and search.strip():
            queryset = filter_students(queryset, search)

        reg = self.request.query_params.get("reg_number")
        if reg:
            queryset = queryset.filter(reg_number_key=normalise_reg_number(reg))
        return queryset

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        # Only searches are audited. Logging every idle page of the browse view
        # would bury the reads that actually mean something.
        query = (request.query_params.get("search") or "").strip()
        if query:
            audit.record(
                request,
                audit.AuditAction.LIST_STUDENTS,
                query=query,
                result_count=response.data.get("count", 0) if hasattr(response, "data") else 0,
            )
        return response

    @action(
        detail=False,
        methods=["post"],
        url_path="import-preview",
        parser_classes=[MultiPartParser],
    )
    def import_preview(self, request):
        """Dry run: parse and validate a CSV, write nothing."""
        if not request.user.can_manage_records:
            return Response(
                {"detail": "Only a registration officer or administrator can import."},
                status=status.HTTP_403_FORBIDDEN,
            )
        upload = request.FILES.get("file")
        if not upload:
            return Response({"file": ["Choose a CSV file."]}, status=status.HTTP_400_BAD_REQUEST)

        parsed = parse_csv(upload)
        return Response(
            {
                "summary": {
                    "to_create": len(parsed["creates"]),
                    "to_update": len(parsed["updates"]),
                    "errors": len(parsed["errors"]),
                },
                # Capped: a preview is for eyeballing, not for reading 5,000 rows.
                "creates": parsed["creates"][:20],
                "updates": parsed["updates"][:20],
                "errors": parsed["errors"][:50],
            }
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="import-commit",
        parser_classes=[MultiPartParser],
    )
    def import_commit(self, request):
        """Parse again and write, in one transaction."""
        if not request.user.can_manage_records:
            return Response(
                {"detail": "Only a registration officer or administrator can import."},
                status=status.HTTP_403_FORBIDDEN,
            )
        upload = request.FILES.get("file")
        if not upload:
            return Response({"file": ["Choose a CSV file."]}, status=status.HTTP_400_BAD_REQUEST)

        parsed = parse_csv(upload)
        update_existing = str(request.data.get("update_existing", "true")).lower() != "false"
        result = commit(parsed, update_existing=update_existing)
        return Response(
            {
                **result,
                "errors": parsed["errors"][:50],
                "detail": (
                    f"Imported {result['created']} new students and updated "
                    f"{result['updated']}. {result['skipped']} rows were skipped."
                ),
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        counts = {
            row["status"]: row["total"]
            for row in Student.objects.values("status").annotate(total=Count("id"))
        }
        return Response(
            {
                "total": sum(counts.values()),
                "by_status": {choice.value: counts.get(choice.value, 0) for choice in StudentStatus},
            }
        )
