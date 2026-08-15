from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    default_gate_name = serializers.CharField(source="default_gate.name", read_only=True)
    can_manage_records = serializers.BooleanField(read_only=True)
    is_admin_role = serializers.BooleanField(read_only=True)
    two_factor_enabled = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone",
            "role",
            "role_display",
            "staff_number",
            "default_gate",
            "default_gate_name",
            "is_active",
            "can_manage_records",
            "is_admin_role",
            "two_factor_enabled",
            "last_login",
        )
        read_only_fields = ("last_login",)

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_two_factor_enabled(self, obj):
        from .twofactor import has_2fa

        return has_2fa(obj)


class UserWriteSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("password",)

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """Returns the token pair plus the profile, so the UI needs only one call.

    Also the enforcement point for two-factor. django_otp's middleware assumes
    sessions; this API issues JWTs, so the check belongs here - a token must
    never be minted without the second factor.
    """

    otp_token = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate(self, attrs):
        from . import twofactor

        token = (attrs.pop("otp_token", "") or "").strip()
        # Password is checked first; a wrong password should never reveal
        # whether the account has 2FA enabled.
        data = super().validate(attrs)

        if twofactor.is_required_for(self.user):
            if not token:
                raise serializers.ValidationError(
                    {
                        "otp_required": True,
                        "detail": "Enter the 6-digit code from your authenticator app.",
                    }
                )
            ok, message = twofactor.verify(self.user, token)
            if not ok:
                raise serializers.ValidationError(
                    {
                        "otp_required": True,
                        "detail": message
                        or "That code is not right, or it has already been used.",
                    }
                )

        data["user"] = UserSerializer(self.user).data
        return data


class TwoFactorConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()


class TwoFactorDisableSerializer(serializers.Serializer):
    """Turning 2FA off is a password-gated action, not a single click."""

    password = serializers.CharField()

    def validate_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("Password is incorrect.")
        return value


class AccessLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source="get_action_display", read_only=True)
    full_name = serializers.SerializerMethodField()
    role_display = serializers.CharField(source="user.get_role_display", read_only=True)

    class Meta:
        from .audit import AccessLog

        model = AccessLog
        fields = (
            "id",
            "user",
            "username",
            "full_name",
            "role_display",
            "action",
            "action_display",
            "query",
            "result_count",
            "subject_reg_number",
            "ip_address",
            "created_at",
        )

    def get_full_name(self, obj):
        return obj.user.get_full_name() if obj.user else obj.username


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value
