import io

import qrcode
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts import audit
from accounts.permissions import CanManageRecords
from notifications.service import (
    notify_registration_approved,
    notify_registration_rejected,
)
from search.indexer import filter_devices

from .models import (
    Device,
    DeviceFlag,
    DeviceStatus,
    FlagReason,
    OwnershipTransfer,
    TemporaryPermit,
    normalise_serial,
)
from .serializers import (
    DeviceFlagSerializer,
    DeviceGateSerializer,
    DeviceSerializer,
    DeviceTransferSerializer,
    OwnershipTransferSerializer,
    TemporaryPermitSerializer,
)

# Prefix written into every QR sticker so the scanner can tell our codes apart
# from random barcodes on a laptop lid.
QR_PREFIX = "CTRACK"


def build_qr_payload(device):
    return f"{QR_PREFIX}:{device.uid}"


class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = (CanManageRecords,)
    filterset_fields = ("status", "device_type", "owner", "is_archived")
    ordering_fields = ("registered_at", "brand", "serial_number", "status")
    # Search runs through the inverted index (see search/indexer.py) rather
    # than DRF's SearchFilter, whose `icontains` cannot use an index.

    def get_queryset(self):
        queryset = (
            Device.objects.select_related("owner", "owner__department", "registered_by")
            .prefetch_related("flags")
        )

        search = self.request.query_params.get("search")
        if search and search.strip():
            queryset = filter_devices(queryset, search)
        if self.action in {"list"} and "is_archived" not in self.request.query_params:
            queryset = queryset.filter(is_archived=False)
        serial = self.request.query_params.get("serial")
        if serial:
            queryset = queryset.filter(serial_key=normalise_serial(serial))
        flagged = self.request.query_params.get("flagged")
        if flagged in {"1", "true", "True"}:
            queryset = queryset.filter(
                Q(flags__is_active=True)
                | Q(status__in=[DeviceStatus.LOST, DeviceStatus.STOLEN])
            ).distinct()
        return queryset

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DeviceGateSerializer
        return DeviceSerializer

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        query = (request.query_params.get("search") or "").strip()
        if query:
            audit.record(
                request,
                audit.AuditAction.LIST_DEVICES,
                query=query,
                result_count=response.data.get("count", 0) if hasattr(response, "data") else 0,
            )
        return response

    def perform_create(self, serializer):
        serializer.save(registered_by=self.request.user)

    @action(detail=True, methods=["get"], url_path="qr")
    def qr(self, request, pk=None):
        """PNG QR sticker for this device, printed and stuck on the chassis."""
        device = self.get_object()
        image = qrcode.make(build_qr_payload(device), box_size=10, border=2)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        response = HttpResponse(buffer.getvalue(), content_type="image/png")
        response["Content-Disposition"] = f'inline; filename="qr-{device.serial_number}.png"'
        return response

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        """Hand a device over to another student and keep the paper trail."""
        device = self.get_object()
        serializer = DeviceTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_owner = serializer.validated_data["to_student_reg_number"]
        if new_owner.pk == device.owner_id:
            return Response(
                {"detail": "That student already owns this device."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            record = OwnershipTransfer.objects.create(
                device=device,
                from_student=device.owner,
                to_student=new_owner,
                reason=serializer.validated_data.get("reason", ""),
                transferred_by=request.user,
            )
            device.owner = new_owner
            device.save(update_fields=["owner", "updated_at"])
        return Response(
            {
                "detail": f"Device transferred to {new_owner.reg_number}.",
                "transfer": OwnershipTransferSerializer(record).data,
                "device": DeviceGateSerializer(device).data,
            }
        )

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        device = self.get_object()
        return Response(
            {
                "transfers": OwnershipTransferSerializer(
                    device.transfers.select_related("from_student", "to_student"), many=True
                ).data,
                "flags": DeviceFlagSerializer(device.flags.all(), many=True).data,
                "permits": TemporaryPermitSerializer(device.permits.all(), many=True).data,
            }
        )

    @action(detail=True, methods=["post"])
    def report_stolen(self, request, pk=None):
        """One-click theft report: sets the status and raises a blocking flag."""
        device = self.get_object()
        details = request.data.get("details", "")
        with transaction.atomic():
            device.status = DeviceStatus.STOLEN
            device.save(update_fields=["status", "updated_at"])
            flag = DeviceFlag.objects.create(
                device=device,
                reason=FlagReason.STOLEN,
                details=details,
                raised_by=request.user,
            )
        return Response(
            {
                "detail": "Device flagged as stolen. It will now be blocked at every gate.",
                "flag": DeviceFlagSerializer(flag).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Accept a self-registration and put it on the active register."""
        device = self.get_object()
        if device.status != DeviceStatus.PENDING:
            return Response(
                {"detail": "Only a pending registration can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset_tag = (request.data.get("asset_tag") or "").strip().upper() or None
        if asset_tag and Device.objects.filter(asset_tag=asset_tag).exclude(pk=device.pk).exists():
            return Response(
                {"asset_tag": ["That asset tag is already on another computer."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        device.status = DeviceStatus.ACTIVE
        if asset_tag:
            device.asset_tag = asset_tag
        # Approval is the point at which a named officer takes responsibility
        # for the record, so that is who it is attributed to.
        device.registered_by = request.user
        device.save(update_fields=["status", "asset_tag", "registered_by", "updated_at"])

        # The student should not have to keep checking the page to find out.
        queued = notify_registration_approved(device)
        return Response(
            {
                "detail": f"{device.serial_number} approved. It will now pass the gates.",
                "owner_notified": bool(queued),
                "device": DeviceGateSerializer(device).data,
            }
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Turn down a self-registration, keeping the reason on the record."""
        device = self.get_object()
        if device.status != DeviceStatus.PENDING:
            return Response(
                {"detail": "Only a pending registration can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reason = (request.data.get("reason") or "").strip()
        if not reason:
            return Response(
                {"reason": ["Say why this registration was turned down."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Archived rather than deleted: the submission itself is part of the
        # audit trail, and the serial stays claimed so it cannot be re-submitted
        # in a loop.
        device.is_archived = True
        device.notes = f"{device.notes}\nRejected by {request.user.get_full_name() or request.user.username}: {reason}".strip()
        device.save(update_fields=["is_archived", "notes", "updated_at"])

        queued = notify_registration_rejected(device, reason)
        return Response(
            {"detail": f"{device.serial_number} rejected.", "owner_notified": bool(queued)}
        )

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """The approval queue: everything students have submitted."""
        queryset = self.get_queryset().filter(
            status=DeviceStatus.PENDING, is_archived=False
        ).order_by("registered_at")
        page = self.paginate_queryset(queryset)
        serializer = DeviceSerializer(page if page is not None else queryset, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        base = Device.objects.filter(is_archived=False)
        by_status = {
            row["status"]: row["total"] for row in base.values("status").annotate(total=Count("id"))
        }
        by_type = {
            row["device_type"]: row["total"]
            for row in base.values("device_type").annotate(total=Count("id"))
        }
        return Response(
            {
                "total": base.count(),
                "by_status": by_status,
                "by_type": by_type,
                "active_flags": DeviceFlag.objects.filter(is_active=True).count(),
                "valid_permits": TemporaryPermit.objects.filter(
                    is_revoked=False, valid_from__lte=timezone.now(), valid_to__gte=timezone.now()
                ).count(),
            }
        )


class DeviceFlagViewSet(viewsets.ModelViewSet):
    serializer_class = DeviceFlagSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("is_active", "reason", "device")
    search_fields = ("device__serial_number", "device__owner__reg_number", "details")
    ordering_fields = ("created_at",)

    def get_queryset(self):
        return DeviceFlag.objects.select_related(
            "device", "device__owner", "raised_by", "resolved_by"
        )

    def perform_create(self, serializer):
        serializer.save(raised_by=self.request.user, is_active=True)

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        flag = self.get_object()
        if not flag.is_active:
            return Response(
                {"detail": "This flag is already resolved."}, status=status.HTTP_400_BAD_REQUEST
            )
        flag.resolve(request.user, request.data.get("resolution_note", ""))
        # Clearing a theft report should also release the device status,
        # otherwise the gate keeps blocking it for a reason nobody can see.
        device = flag.device
        if flag.reason in {FlagReason.STOLEN, FlagReason.LOST} and device.status in {
            DeviceStatus.STOLEN,
            DeviceStatus.LOST,
        }:
            device.status = DeviceStatus.ACTIVE
            device.save(update_fields=["status", "updated_at"])
        return Response(DeviceFlagSerializer(flag).data)


class TemporaryPermitViewSet(viewsets.ModelViewSet):
    serializer_class = TemporaryPermitSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("is_revoked", "device")
    search_fields = ("bearer_name", "bearer_id_number", "device__serial_number")
    ordering_fields = ("valid_to", "created_at")

    def get_queryset(self):
        queryset = TemporaryPermit.objects.select_related("device", "device__owner", "issued_by")
        if self.request.query_params.get("valid") in {"1", "true", "True"}:
            now = timezone.now()
            queryset = queryset.filter(is_revoked=False, valid_from__lte=now, valid_to__gte=now)
        return queryset

    def perform_create(self, serializer):
        serializer.save(issued_by=self.request.user)

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        permit = self.get_object()
        permit.is_revoked = True
        permit.save(update_fields=["is_revoked"])
        return Response(TemporaryPermitSerializer(permit).data)


class OwnershipTransferViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OwnershipTransferSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("device", "to_student", "from_student")
    ordering_fields = ("created_at",)

    def get_queryset(self):
        return OwnershipTransfer.objects.select_related(
            "device", "from_student", "to_student", "transferred_by"
        )
