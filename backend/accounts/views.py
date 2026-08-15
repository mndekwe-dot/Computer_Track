from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from . import twofactor
from .audit import AccessLog
from .permissions import IsAdminRole
from .serializers import (
    AccessLogSerializer,
    ChangePasswordSerializer,
    LoginSerializer,
    TwoFactorConfirmSerializer,
    TwoFactorDisableSerializer,
    UserSerializer,
    UserWriteSerializer,
)

User = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
    throttle_scope = "login"


class MeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        """Lets a guard update their own phone and working gate, nothing else."""
        allowed = {"phone", "default_gate", "first_name", "last_name", "email"}
        payload = {k: v for k, v in request.data.items() if k in allowed}
        serializer = UserSerializer(request.user, data=payload, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Password updated."}, status=status.HTTP_200_OK)


class TwoFactorView(APIView):
    """Enrol, confirm and remove the second factor on your own account.

    Always your own - there is no path here to enrol or disable 2FA on somebody
    else's account, not even for an administrator. An admin who can silently
    disable another admin's second factor defeats the point of having one.
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response(
            {
                "enabled": twofactor.has_2fa(request.user),
                "required_at_login": twofactor.is_required_for(request.user),
                "recommended": request.user.is_admin_role,
            }
        )

    def post(self, request):
        """Begin enrolment: returns a QR code and the secret to type by hand."""
        if twofactor.has_2fa(request.user):
            return Response(
                {"detail": "Two-factor is already on. Turn it off first to re-enrol."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(twofactor.begin_enrolment(request.user), status=status.HTTP_201_CREATED)

    def put(self, request):
        """Confirm enrolment with a code from the app."""
        serializer = TwoFactorConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ok, message = twofactor.confirm_enrolment(
            request.user, serializer.validated_data["token"]
        )
        if not ok:
            return Response({"token": [message]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": message, "enabled": True})

    def delete(self, request):
        """Turn it off. Requires the account password."""
        serializer = TwoFactorDisableSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        twofactor.disable(request.user)
        return Response({"detail": "Two-factor authentication turned off.", "enabled": False})


class AccessLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Who looked up whom. Read-only, admin-only, and never editable.

    The point of an audit log is that the people it covers cannot tidy it up,
    so there is no write path here at all - not even for administrators.
    """

    serializer_class = AccessLogSerializer
    permission_classes = (IsAdminRole,)
    filterset_fields = ("action", "user")
    ordering_fields = ("created_at",)

    def get_queryset(self):
        queryset = AccessLog.objects.select_related("user")
        params = self.request.query_params

        if params.get("date_from"):
            queryset = queryset.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            queryset = queryset.filter(created_at__date__lte=params["date_to"])
        if params.get("q"):
            term = params["q"].strip()
            queryset = queryset.filter(
                Q(username__icontains=term)
                | Q(query__icontains=term)
                | Q(subject_reg_number__icontains=term)
            )
        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Busiest accounts over the last week - where to look for a problem."""
        since = timezone.now() - timedelta(days=7)
        recent = AccessLog.objects.filter(created_at__gte=since)
        by_user = (
            recent.values("username")
            .annotate(reads=Count("id"))
            .order_by("-reads")[:10]
        )
        by_action = {
            row["action"]: row["total"]
            for row in recent.values("action").annotate(total=Count("id"))
        }
        return Response(
            {
                "since": since,
                "total_reads": recent.count(),
                "busiest_accounts": list(by_user),
                "by_action": by_action,
            }
        )


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("default_gate").all()
    permission_classes = (IsAdminRole,)
    filterset_fields = ("role", "is_active", "default_gate")
    search_fields = ("username", "first_name", "last_name", "staff_number", "email")
    ordering_fields = ("username", "first_name", "role", "last_login")

    def get_serializer_class(self):
        if self.action in {"list", "retrieve"}:
            return UserSerializer
        return UserWriteSerializer

    @action(detail=True, methods=["post"])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get("new_password", "")
        if len(new_password) < 8:
            return Response(
                {"new_password": ["Password must be at least 8 characters."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.set_password(new_password)
        user.save(update_fields=["password"])
        return Response({"detail": f"Password reset for {user.username}."})
