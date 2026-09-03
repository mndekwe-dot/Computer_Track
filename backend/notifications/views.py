"""Reading and rewording what the system says to people.

Two screens sit on this: the message editor, and an outbox view that answers
"was the student actually told?" - a question that used to require database
access, and that comes up every time somebody disputes a gate decision.
"""

from django.db.models import Count, Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from accounts.permissions import CanManageRecords
from config.throttles import WriteThrottle

from .models import EDITABLE_KINDS, Notification, NotificationTemplate, Status
from .templating import DEFAULTS, PLACEHOLDERS, invalidate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    placeholders = serializers.SerializerMethodField()
    default_body = serializers.SerializerMethodField()

    class Meta:
        model = NotificationTemplate
        fields = (
            "id",
            "kind",
            "kind_display",
            "channel",
            "channel_display",
            "subject",
            "body",
            "is_active",
            "placeholders",
            "default_body",
            "updated_at",
        )
        read_only_fields = ("updated_at",)

    def get_placeholders(self, obj):
        """What this message may refer to.

        Sent with the template because a registrar cannot guess `{gate}` and
        should not have to read the source to find out.
        """
        return PLACEHOLDERS.get(obj.kind, [])

    def get_default_body(self, obj):
        """The wording it shipped with, so an edit can always be undone."""
        return DEFAULTS.get((obj.kind, obj.channel), ("", ""))[1]

    def validate_kind(self, value):
        if value not in EDITABLE_KINDS:
            raise serializers.ValidationError(
                "That message is read by staff during an incident and its wording is part of "
                "the procedure, so it is not editable here."
            )
        return value

    def validate_body(self, value):
        if not (value or "").strip():
            raise serializers.ValidationError(
                "A message cannot be empty. To stop sending this one, untick 'in use' instead - "
                "that falls back to the built-in wording rather than sending nothing."
            )
        return value


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationTemplateSerializer
    permission_classes = (CanManageRecords,)
    throttle_classes = (WriteThrottle,)
    filterset_fields = ("kind", "channel", "is_active")
    pagination_class = None

    def get_queryset(self):
        return NotificationTemplate.objects.filter(kind__in=EDITABLE_KINDS)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)
        invalidate()

    def perform_create(self, serializer):
        serializer.save(updated_by=self.request.user)
        invalidate()

    @action(detail=True, methods=["post"])
    def preview(self, request, pk=None):
        """Render this template against a worked example.

        Editing a message with placeholders in it and no way to see the result
        is how `{studnet_name}` reaches four thousand people.
        """
        template = self.get_object()
        sample = {
            "student_first_name": "Aline",
            "student_name": "Aline Uwase",
            "reg_number": "218001234",
            "device": "Dell Latitude 5420",
            "serial": "DL99887766",
            "brand": "Dell",
            "asset_tag": " Its asset tag is UNI-024/01.",
            "gate": "Main Gate",
            "time": "18:42 on 04 Sep",
            "reason": "The serial on the machine does not match the one submitted.",
            "report": "reported stolen",
            "university": "the university",
            "office": "the registration office",
            "security_phone": "0788 000 000",
            "support_email": "registry@example.edu",
            "support_phone": "0788 111 111",
        }
        # Rendered from what was submitted, not from what is saved, so the
        # preview reflects the edit in the box rather than the last save.
        body = request.data.get("body", template.body)
        subject = request.data.get("subject", template.subject)
        from .templating import render

        return Response(
            {
                "subject": render(subject, sample),
                "body": render(body, sample),
                "channel": template.channel,
            }
        )

    @action(detail=True, methods=["post"], url_path="reset")
    def reset(self, request, pk=None):
        """Put one message back to the wording it shipped with."""
        template = self.get_object()
        subject, body = DEFAULTS.get((template.kind, template.channel), ("", ""))
        if not body:
            return Response(
                {"detail": "There is no built-in wording for this message."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        template.subject = subject
        template.body = body
        template.is_active = True
        template.updated_by = request.user
        template.save(update_fields=["subject", "body", "is_active", "updated_by", "updated_at"])
        invalidate()
        return Response(NotificationTemplateSerializer(template).data)


class NotificationSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    channel_display = serializers.CharField(source="get_channel_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    student_name = serializers.CharField(
        source="student.full_name", read_only=True, allow_null=True, default=None
    )
    device_serial = serializers.CharField(
        source="device.serial_number", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = Notification
        fields = (
            "id",
            "kind",
            "kind_display",
            "channel",
            "channel_display",
            "recipient",
            "subject",
            "body",
            "status",
            "status_display",
            "attempts",
            "last_error",
            "next_attempt_at",
            "student",
            "student_name",
            "device",
            "device_serial",
            "created_at",
            "sent_at",
        )


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """The outbox, read-only.

    Answers "was the owner actually told, and when" without anybody needing
    database access. Read-only because editing a sent message would make the
    record a worse account of what happened than no record at all.
    """

    serializer_class = NotificationSerializer
    permission_classes = (CanManageRecords,)
    filterset_fields = ("status", "channel", "kind", "student", "device")
    search_fields = ("recipient", "subject", "body")
    ordering_fields = ("created_at", "sent_at", "attempts")

    def get_queryset(self):
        return Notification.objects.select_related("student", "device")

    @action(detail=False, methods=["get"])
    def summary(self, request):
        counts = Notification.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=Status.PENDING)),
            sent=Count("id", filter=Q(status=Status.SENT)),
            failed=Count("id", filter=Q(status=Status.FAILED)),
        )
        by_channel = {
            row["channel"]: row["total"]
            for row in Notification.objects.values("channel").annotate(total=Count("id"))
        }
        return Response(
            {
                **{key: value or 0 for key, value in counts.items()},
                "by_channel": by_channel,
                # Surfaced so a failing provider is visible on the screen
                # rather than only in a log nobody is watching.
                "recent_errors": list(
                    Notification.objects.filter(status=Status.FAILED)
                    .exclude(last_error="")
                    .order_by("-created_at")
                    .values("id", "recipient", "channel", "last_error", "created_at")[:5]
                ),
            }
        )

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        """Send one failed message again, now."""
        notification = self.get_object()
        if notification.status == Status.SENT:
            return Response(
                {"detail": "That message was already sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notification.status = Status.PENDING
        notification.attempts = 0
        notification.last_error = ""
        notification.next_attempt_at = None
        notification.save(
            update_fields=["status", "attempts", "last_error", "next_attempt_at"]
        )

        from .service import send_one

        sent = send_one(notification)
        notification.refresh_from_db()
        return Response(
            {
                "detail": "Sent." if sent else f"Still failing: {notification.last_error}",
                "sent": sent,
                "notification": NotificationSerializer(notification).data,
            }
        )
