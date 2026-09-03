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


Registering somebody else's computer
------------------------------------

The obvious attack on a self-service register is to put a stolen laptop on it
under your own name, and then walk out through the gate with the system's
blessing. Identity verification does not touch that at all: the thief may be a
perfectly real, perfectly enrolled student.

Five things work against it, none of them sufficient alone.

*The serial is already claimed.* The real owner registered it first, so the
submission collides. The reply never says who holds it - that would turn the
form into a lookup tool - but the collision is recorded, and if the existing
record is one somebody has reported stolen, the security office is told.

*Approval is in person.* A submission is PENDING and blocked at every gate
until an officer sees the machine. That is the check that actually catches the
unregistered stolen laptop, and it is a human one; the software's job is to
make sure the machine cannot leave before it happens.

*A ceiling on how many.* One student with nine computers is a question worth
asking. The limit is a rule the registration office sets.

*Repeat submissions are counted.* One student trying serial after serial is
the signature of somebody working through a bag. It does not block them - a
student with a broken keyboard retypes a serial too - it puts them in front of
an officer.

*The owner is told.* Every message this system sends exists so that a person
who has been impersonated finds out quickly, rather than at the end of term.

What none of this stops: a thief who registers a machine before its owner
does, and is not asked for a receipt. That is why approval happens in person,
and why `registration.require_ownership_proof` exists.
"""

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import client_ip
from campus import equipment
from campus.rules import public_rules, rule
from devices.models import (
    AttemptOutcome,
    Device,
    DeviceFlag,
    DeviceStatus,
    FlagReason,
    RegistrationAttempt,
    normalise_serial,
)
from notifications.service import notify_owner_of_missing_report

from .models import Student, normalise_reg_number

logger = logging.getLogger(__name__)

# Kept deliberately identical for "no such student" and "details do not match",
# so the form cannot be used to discover who is enrolled.
VERIFY_FAILED = (
    "Those details do not match a student record. Check your registration number and the "
    "email or national ID the university holds for you, or visit the registration office."
)


def record_attempt(request, outcome, reg_number="", student=None, serial="", brand="", detail="", existing=None):
    """Write one row to the attempt log. Never raises.

    Deliberately wrapped: this is a security record, and a security record
    that can 500 the endpoint it observes is a denial-of-service switch.
    """
    try:
        return RegistrationAttempt.objects.create(
            reg_number=(reg_number or "")[:40],
            student=student,
            serial_number=(serial or "")[:80],
            serial_key=normalise_serial(serial)[:80],
            brand=(brand or "")[:60],
            outcome=outcome,
            detail=(detail or "")[:300],
            existing_device=existing,
            ip_address=client_ip(request) if request else None,
        )
    except Exception:
        logger.exception("Could not record a registration attempt")
        return None


def alert_security(device, attempt, reg_number):
    """Tell staff that a computer reported missing was just submitted again.

    This is the one outcome worth waking somebody for. A serial that somebody
    has reported stolen turning up on a registration form means the machine is
    on campus, right now, in the hands of whoever filled the form in.

    The person submitting is told nothing beyond the ordinary "already
    registered" message. Telling them would be telling them to run.
    """
    from notifications.models import Kind
    from notifications.service import notify_staff
    from django.conf import settings

    recipients = getattr(settings, "AUDIT_ALERT_RECIPIENTS", [])
    if not recipients:
        logger.warning(
            "Serial %s is reported %s and was just submitted by %s, but "
            "AUDIT_ALERT_RECIPIENTS is empty so nobody was told.",
            device.serial_number,
            device.status,
            reg_number,
        )
        return

    body = (
        f"A computer reported {device.get_status_display().lower()} has just been submitted "
        f"to the public registration form.\n\n"
        f"Serial: {device.serial_number}\n"
        f"Registered to: {device.owner.reg_number if device.owner else 'university property'}"
        f" ({device.owner.full_name if device.owner else '-'})\n"
        f"Submitted under registration number: {reg_number}\n"
        f"Submitted from: {attempt.ip_address if attempt else 'unknown'}\n"
        f"Time: {timezone.localtime().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"The person submitting was told only that the serial is already registered. They "
        f"have not been alerted.\n\n"
        f"This is worth acting on quickly: it means the computer is on campus now.\n"
    )
    notify_staff(
        Kind.SUSPICIOUS,
        recipients,
        f"Computer reported {device.get_status_display().lower()} was just re-submitted",
        body,
    )


def verify_student(reg_number, verification):
    """Find the student only if the supplied detail matches what is on file."""
    student = Student.objects.filter(reg_number_key=normalise_reg_number(reg_number)).first()
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
    # Declared with no validators so DRF does not attach its own uniqueness
    # check. That check would run first and win, which had two consequences:
    # the student got "device with this serial number already exists" instead
    # of a sentence telling them what to do, and - the reason it matters here -
    # the collision was never recorded, because `validate_serial_number` below
    # is where an attempt gets logged and security gets alerted.
    #
    # Uniqueness is still enforced. It is enforced there, against the
    # normalised key, which also catches "dl-9988 7766" as the same machine.
    serial_number = serializers.CharField(validators=[])

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
            "purchase_details",
            # A photo of the machine is worth more to a guard than any written
            # description, so the student is asked for one up front.
            "photo",
        )
        extra_kwargs = {
            "brand": {"required": True, "allow_blank": False},
            "serial_number": {"required": True, "allow_blank": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # `request` is threaded through so a refusal can be logged with the
        # address it came from. Without it the attempt log records the pattern
        # but not where it came from, which halves its value.
        self.request = self.context.get("request")

    def validate_serial_number(self, value):
        key = normalise_serial(value)
        if not key:
            raise serializers.ValidationError("Serial number is required.")

        existing = Device.objects.select_related("owner").filter(serial_key=key).first()
        if existing:
            # Everything below happens before the reply, and the reply is the
            # same either way. The submitter learns only that the serial is
            # taken; the office learns the rest.
            missing = existing.status in {DeviceStatus.STOLEN, DeviceStatus.LOST}
            attempt = record_attempt(
                self.request,
                AttemptOutcome.MATCHED_MISSING if missing else AttemptOutcome.DUPLICATE_SERIAL,
                reg_number=self.initial_data.get("reg_number", ""),
                serial=value,
                brand=self.initial_data.get("brand", ""),
                detail=(
                    f"Existing record is {existing.get_status_display()}."
                    if missing
                    else "Serial already on the register."
                ),
                existing=existing,
            )
            if missing:
                alert_security(existing, attempt, self.initial_data.get("reg_number", ""))

            # Never name the current owner - that would leak the register to
            # anyone who can guess a serial number.
            raise serializers.ValidationError(
                "This serial number is already registered. If this is your computer, take it "
                "to the registration office rather than registering it again."
            )
        return value.strip().upper()

    def validate_device_type(self, value):
        if not equipment.is_valid(value, for_students=True):
            raise serializers.ValidationError("Choose a valid type of equipment.")
        return value

    def validate_photo(self, value):
        if not value and rule("registration.require_photo"):
            raise serializers.ValidationError(
                "A photograph of the computer is required. A guard compares the machine in "
                "front of them against it."
            )
        return value

    def validate(self, attrs):
        student = verify_student(attrs.pop("reg_number"), attrs.pop("verification"))

        if rule("registration.require_photo") and not attrs.get("photo"):
            raise serializers.ValidationError(
                {
                    "photo": "A photograph of the computer is required. A guard compares the "
                    "machine in front of them against it."
                }
            )
        if rule("registration.require_ownership_proof") and not (
            attrs.get("purchase_details") or ""
        ).strip():
            raise serializers.ValidationError(
                {
                    "purchase_details": "Say where and roughly when you bought this. It is what "
                    "settles a dispute later if two people claim the same computer."
                }
            )

        self._check_limit(student)
        self._check_velocity(student, attrs)
        attrs["student"] = student
        return attrs

    def _check_limit(self, student):
        """A ceiling on how many computers one student may hold.

        Counts pending submissions too. Counting only approved ones would let
        somebody queue twenty and wait, which is the behaviour the limit is
        there to notice.
        """
        limit = rule("registration.max_devices_per_student")
        if not limit:
            return
        held = Device.objects.filter(owner=student, is_archived=False).count()
        if held >= limit:
            record_attempt(
                self.request,
                AttemptOutcome.LIMIT_REACHED,
                reg_number=student.reg_number,
                student=student,
                serial=self.initial_data.get("serial_number", ""),
                brand=self.initial_data.get("brand", ""),
                detail=f"Already holds {held}, limit is {limit}.",
            )
            raise serializers.ValidationError(
                {
                    "serial_number": (
                        f"You already have {held} computers on the register, which is the most "
                        f"one student may register online. To add another, take it to the "
                        f"registration office."
                    )
                }
            )

    def _check_velocity(self, student, attrs):
        """Count recent submissions from this student.

        Does not refuse. A student whose first attempt had a typo in the
        serial should not be locked out, and a limit that stops a genuine
        student is a limit that gets switched off. What it does is mark the
        submission for review, so an officer sees the pattern before approving
        the fifth laptop this week.
        """
        window = rule("registration.velocity_window_hours")
        ceiling = rule("registration.velocity_max_attempts")
        since = timezone.now() - timezone.timedelta(hours=window)
        recent = RegistrationAttempt.objects.filter(
            student=student, created_at__gte=since
        ).count()
        if recent >= ceiling:
            record_attempt(
                self.request,
                AttemptOutcome.TOO_MANY_ATTEMPTS,
                reg_number=student.reg_number,
                student=student,
                serial=attrs.get("serial_number", ""),
                brand=attrs.get("brand", ""),
                detail=f"{recent} submissions in the last {window} hours.",
            )
            attrs["_flag_for_review"] = (
                f"{recent + 1} registration submissions in {window} hours."
            )

    def create(self, validated_data):
        student = validated_data.pop("student")
        review_note = validated_data.pop("_flag_for_review", "")

        notes = "Submitted by the student through the public registration form."
        if review_note:
            notes += f"\nFlagged for review: {review_note}"

        with transaction.atomic():
            device = Device.objects.create(
                **validated_data,
                owner=student,
                # A self-registration is a request, not a fact. It stays
                # PENDING, and therefore blocked at every gate, until a
                # registrar approves it.
                status=DeviceStatus.PENDING,
                notes=notes,
            )
            record_attempt(
                self.request,
                AttemptOutcome.ACCEPTED,
                reg_number=student.reg_number,
                student=student,
                serial=device.serial_number,
                brand=device.brand,
                detail=review_note,
            )
        return device


class PublicRegistrationView(APIView):
    """POST /api/public/register-computer/ - multipart, because of the photo."""

    permission_classes = ()
    authentication_classes = ()
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    throttle_scope = "public-form"

    def post(self, request):
        if not rule("registration.public_form_enabled"):
            return Response(
                {
                    "detail": (
                        "Online registration is closed at the moment. Please take your computer "
                        f"to {rule('branding.office_name')} to have it registered."
                    ),
                    "code": "registration_closed",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = PublicRegistrationSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        return Response(
            {
                "detail": (
                    f"Registration received. Take the computer to {rule('branding.office_name')} "
                    "to have it approved and to collect its sticker - until then it will be held "
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

        from devices import queries

        owned = (
            queries.for_list(Device.objects.filter(owner=student, is_archived=False))
            .order_by("-registered_at")
        )
        return Response(
            {
                "student": {"reg_number": student.reg_number, "full_name": student.full_name},
                "computers": [
                    {
                        "serial_number": device.serial_number,
                        "label": device.label,
                        "type": device.device_type_label,
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
    office = rule("branding.office_name")
    if device.status == DeviceStatus.PENDING:
        return (
            f"Waiting for approval. Bring the computer to {office} - it will be held at the "
            "gate until it is approved."
        )
    if device.status == DeviceStatus.ACTIVE and device.is_blocked:
        return f"There is a hold on this computer. Please contact {office}."
    if device.status == DeviceStatus.ACTIVE:
        return "Approved. You may carry this through any gate."
    if device.status in {DeviceStatus.LOST, DeviceStatus.STOLEN}:
        return "Reported missing. Every gate will stop it. Contact security immediately."
    return f"No longer on the active register. Speak to {office}."


class PublicLookupChoicesView(APIView):
    """Everything the public pages need to render themselves.

    Equipment types and the branding text both come from here, so a university
    that renames itself or adds a new kind of equipment does not need the
    frontend rebuilt.
    """

    permission_classes = ()
    authentication_classes = ()
    throttle_scope = "public-form"

    def get(self, request):
        return Response(
            {
                "device_types": equipment.student_choices(),
                "settings": public_rules(),
            }
        )


class PublicMissingReportSerializer(serializers.Serializer):
    """Report your own computer lost or stolen, without an account.

    The obvious objection to an open endpoint that blocks a computer is that
    somebody could block a computer that is not theirs. Three things bound
    that. It takes the same identity check as registration, so a reporter
    needs the reg number *and* the email or national ID already on file. It
    can only touch a device that belongs to the verified student. And the
    owner is emailed the moment it happens, so a report they did not make
    cannot sit there unnoticed.

    Against that: a stolen laptop is leaving campus while anyone deliberates,
    and the alternative is a student walking to the registration office during
    opening hours. The hold is reversible by any registrar in one click; the
    laptop is not.
    """

    reg_number = serializers.CharField()
    verification = serializers.CharField()
    serial_number = serializers.CharField()
    kind = serializers.ChoiceField(choices=[FlagReason.STOLEN, FlagReason.LOST])
    details = serializers.CharField(allow_blank=True, required=False)

    def validate(self, attrs):
        student = verify_student(attrs.pop("reg_number"), attrs.pop("verification"))
        device = Device.objects.filter(
            owner=student,
            serial_key=normalise_serial(attrs["serial_number"]),
            is_archived=False,
        ).first()
        if not device:
            # Says nothing about whether the serial exists on somebody else's
            # record, which would turn this into a lookup tool.
            raise serializers.ValidationError(
                {
                    "serial_number": (
                        "No computer with that serial is registered to you. Check the serial, "
                        "or use 'Check my computers' to see what is on your record."
                    )
                }
            )
        if device.status in {DeviceStatus.LOST, DeviceStatus.STOLEN}:
            raise serializers.ValidationError(
                {
                    "serial_number": "This computer is already reported missing. Every gate is "
                    "already stopping it."
                }
            )
        attrs["device"] = device
        return attrs


class PublicMissingReportView(APIView):
    """POST /api/public/report-missing/ - block a computer you own, now."""

    permission_classes = ()
    authentication_classes = ()
    throttle_scope = "public-form"

    def post(self, request):
        if not rule("registration.missing_report_enabled"):
            return Response(
                {
                    "detail": (
                        "Online reporting is closed at the moment. Contact security control "
                        "directly."
                    ),
                    "code": "reporting_closed",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = PublicMissingReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.validated_data["device"]
        kind = serializer.validated_data["kind"]
        details = serializer.validated_data.get("details", "").strip()

        stolen = kind == FlagReason.STOLEN
        with transaction.atomic():
            device.status = DeviceStatus.STOLEN if stolen else DeviceStatus.LOST
            device.save(update_fields=["status", "updated_at"])
            DeviceFlag.objects.create(
                device=device,
                reason=kind,
                details=(f"Reported by the owner through the public form. {details}").strip(),
                # No `raised_by`: nobody signed in raised this. The flag list
                # shows it as an owner report rather than attributing it to a
                # member of staff who had nothing to do with it.
                raised_by=None,
            )

        notify_owner_of_missing_report(device, "Reported stolen" if stolen else "Reported lost")

        security_phone = rule("branding.security_phone")
        contact = f" Call security control on {security_phone}." if security_phone else ""
        return Response(
            {
                "detail": (
                    "Reported. Every gate on campus will now stop this computer. "
                    f"Take your student ID to {rule('branding.office_name')} to follow it up, "
                    f"and report a theft to security control as well.{contact}"
                ),
                "serial_number": device.serial_number,
                "status": device.status,
            },
            status=status.HTTP_201_CREATED,
        )
