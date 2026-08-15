"""The public student form - no login, no account, no portal.

A student fills this in from their phone, and the registration office approves
what comes through. Two rules make an open endpoint safe enough to expose:

1. It can only ever *create a PENDING record*. It cannot approve anything, edit
   anything that already exists, or read the register. A registrar is still the
   one who decides, exactly as before.
2. Identity is checked against details already on the student's record, so a
   passer-by cannot register a laptop against somebody else's reg number.

Anything this endpoint cannot verify, it refuses and sends the student to the
registration office in person.
"""

from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from devices.models import Device, DeviceStatus, DeviceType, normalise_serial

from .models import Student, normalise_reg_number

# Kept deliberately identical for "no such student" and "details do not match",
# so the form cannot be used to discover who is enrolled.
VERIFY_FAILED = (
    "Those details do not match a student record. Check your registration number and the "
    "email or national ID the university holds for you, or visit the registration office."
)


def verify_student(reg_number, verification):
    """Find the student only if the supplied detail matches what is on file."""
    student = Student.objects.filter(
        reg_number_key=normalise_reg_number(reg_number)
    ).first()
    if not student:
        raise serializers.ValidationError({"verification": VERIFY_FAILED})

    supplied = (verification or "").strip().lower()
    on_file = {
        (student.national_id or "").strip().lower(),
        (student.email or "").strip().lower(),
    }
    on_file.discard("")

    if not on_file:
        raise serializers.ValidationError(
            {
                "verification": "Your record has no email or national ID on file, so it cannot "
                "be checked automatically. Please register at the registration office."
            }
        )
    if supplied not in on_file:
        raise serializers.ValidationError({"verification": VERIFY_FAILED})

    if not student.is_clear_to_pass:
        raise serializers.ValidationError(
            {
                "reg_number": f"This student record is {student.get_status_display().lower()}. "
                "Please speak to the registration office."
            }
        )
    return student


class PublicRegistrationSerializer(serializers.ModelSerializer):
    """What a student may tell us about their own computer.

    Owner, status, asset tag and every approval field are absent on purpose:
    they are set by the server or by a registrar, never by the form.
    """

    reg_number = serializers.CharField(write_only=True)
    verification = serializers.CharField(
        write_only=True,
        help_text="The email address or national ID the university holds for you.",
    )

    class Meta:
        model = Device
        fields = (
            "reg_number",
            "verification",
            "serial_number",
            "device_type",
            "brand",
            "model_name",
            "colour",
            "distinguishing_marks",
            # A photo of the machine is worth more to a guard than any written
            # description, so the student is asked for one up front.
            "photo",
        )
        extra_kwargs = {
            "brand": {"required": True, "allow_blank": False},
            "serial_number": {"required": True, "allow_blank": False},
        }

    def validate_serial_number(self, value):
        key = normalise_serial(value)
        if not key:
            raise serializers.ValidationError("Serial number is required.")
        if Device.objects.filter(serial_key=key).exists():
            # Never name the current owner - that would leak the register to
            # anyone who can guess a serial number.
            raise serializers.ValidationError(
                "This serial number is already registered. If this is your computer, take it "
                "to the registration office rather than registering it again."
            )
        return value.strip().upper()

    def validate_device_type(self, value):
        if value not in DeviceType.values:
            raise serializers.ValidationError("Choose a valid type of equipment.")
        return value

    def validate(self, attrs):
        attrs["student"] = verify_student(attrs.pop("reg_number"), attrs.pop("verification"))
        return attrs

    def create(self, validated_data):
        student = validated_data.pop("student")
        return Device.objects.create(
            **validated_data,
            owner=student,
            # A self-registration is a request, not a fact. It stays PENDING,
            # and therefore blocked at every gate, until a registrar approves.
            status=DeviceStatus.PENDING,
            notes="Submitted by the student through the public registration form.",
        )


class PublicRegistrationView(APIView):
    """POST /api/public/register-computer/ - multipart, because of the photo."""

    permission_classes = ()
    authentication_classes = ()
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    throttle_scope = "public-form"

    def post(self, request):
        serializer = PublicRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        return Response(
            {
                "detail": (
                    "Registration received. Take the computer to the registration office to "
                    "have it approved and to collect its sticker - until then it will be held "
                    "at the gate."
                ),
                "reference": str(device.uid)[:8].upper(),
                "serial_number": device.serial_number,
                "status": device.status,
            },
            status=status.HTTP_201_CREATED,
        )


class PublicStatusSerializer(serializers.Serializer):
    reg_number = serializers.CharField()
    verification = serializers.CharField()


class PublicStatusView(APIView):
    """POST /api/public/my-computers/ - "has mine been approved yet?"

    Uses exactly the same verification as the registration form, so it exposes
    nothing the form does not already require.
    """

    permission_classes = ()
    authentication_classes = ()
    throttle_scope = "public-form"

    def post(self, request):
        serializer = PublicStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = verify_student(
            serializer.validated_data["reg_number"], serializer.validated_data["verification"]
        )

        owned = (
            Device.objects.filter(owner=student, is_archived=False)
            .prefetch_related("flags")
            .order_by("-registered_at")
        )
        return Response(
            {
                "student": {"reg_number": student.reg_number, "full_name": student.full_name},
                "computers": [
                    {
                        "serial_number": device.serial_number,
                        "label": device.label,
                        "asset_tag": device.asset_tag,
                        "status": device.status,
                        "status_display": device.get_status_display(),
                        "registered_at": device.registered_at,
                        "guidance": guidance_for(device),
                    }
                    for device in owned
                ],
            }
        )


def guidance_for(device):
    """Plain-language next step, so a student is never left guessing."""
    if device.status == DeviceStatus.PENDING:
        return (
            "Waiting for approval. Bring the computer to the registration office - it will be "
            "held at the gate until it is approved."
        )
    if device.status == DeviceStatus.ACTIVE and device.is_blocked:
        return "There is a hold on this computer. Please contact the registration office."
    if device.status == DeviceStatus.ACTIVE:
        return "Approved. You may carry this through any gate."
    if device.status in {DeviceStatus.LOST, DeviceStatus.STOLEN}:
        return "Reported missing. Every gate will stop it. Contact security immediately."
    return "No longer on the active register. Speak to the registration office."


class PublicLookupChoicesView(APIView):
    """Equipment types for the form's dropdown, so the list lives in one place."""

    permission_classes = ()
    authentication_classes = ()
    throttle_scope = "public-form"

    def get(self, request):
        return Response(
            {
                "device_types": [
                    {"value": value, "label": label} for value, label in DeviceType.choices
                ]
            }
        )
