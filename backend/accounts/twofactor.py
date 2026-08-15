"""Two-factor authentication for administrator accounts.

An administrator reaches every portal, can reset any password and can read the
whole register. A single leaked admin password is therefore the worst thing
that can happen to this system, and a password is the only thing standing in
the way.

Design notes:

- **TOTP only.** No SMS second factor: the phone number lives in the same
  database as the account, so an attacker with database access would have both.
  An authenticator app keeps the second factor genuinely separate.
- **Enforced in the login serializer, not middleware.** `django_otp`'s
  middleware is built around sessions; this API is JWT. Checking at the point
  tokens are issued is the equivalent, and means a token is never minted
  without the second factor.
- **Enrolment is two steps.** Creating a device does not arm it - the user must
  prove they can generate a code first, otherwise a mistyped setup would lock
  them out of their own account.
- **Existing admins are not locked out.** 2FA is required only once an account
  has a *confirmed* device, so it can be rolled out account by account.
"""

import base64
import io
import os

import qrcode
from django.conf import settings
from django_otp.plugins.otp_totp.models import TOTPDevice

DEVICE_NAME = "default"


def get_device(user, confirmed=None):
    query = TOTPDevice.objects.filter(user=user, name=DEVICE_NAME)
    if confirmed is not None:
        query = query.filter(confirmed=confirmed)
    return query.first()


def has_2fa(user):
    """Is this account actually protected right now?"""
    return bool(user and user.is_authenticated and get_device(user, confirmed=True))


def is_required_for(user):
    """Whether this account must present a code at login.

    Only administrators, and only once they have finished enrolling. That lets
    the university turn it on one account at a time instead of locking out the
    whole office on deployment day.
    """
    if not user or not getattr(user, "is_admin_role", False):
        return False
    return has_2fa(user)


def begin_enrolment(user):
    """Create (or reset) an unconfirmed device and return what to scan.

    Re-running this before confirming issues a fresh secret, so a half-finished
    setup can simply be started again.
    """
    TOTPDevice.objects.filter(user=user, name=DEVICE_NAME, confirmed=False).delete()

    device = TOTPDevice.objects.create(
        user=user,
        name=DEVICE_NAME,
        confirmed=False,
        key=os.urandom(20).hex(),
    )

    issuer = getattr(settings, "UNIVERSITY_NAME", "Computer Track")
    uri = device.config_url
    return {
        "otpauth_url": uri,
        # The raw secret, for anyone who cannot scan a QR code.
        "secret": base64.b32encode(bytes.fromhex(device.key)).decode().rstrip("="),
        "issuer": issuer,
        "qr_png_base64": _qr_data_uri(uri),
    }


def _qr_data_uri(uri):
    image = qrcode.make(uri, box_size=6, border=2)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _throttle_message(device):
    """django-otp locks a device briefly after failed attempts.

    Worth saying out loud: otherwise a user who mistypes once is told their
    next - correct - code is wrong, and concludes the setup is broken.
    """
    allowed, detail = device.verify_is_allowed()
    if allowed:
        return None

    from django.utils import timezone

    locked_until = (detail or {}).get("locked_until")
    seconds = 0
    if locked_until:
        seconds = max(0, int((locked_until - timezone.now()).total_seconds()) + 1)
    wait = f" Try again in about {seconds} second{'s' if seconds != 1 else ''}." if seconds else " Try again shortly."
    return f"Too many incorrect codes, so this device is locked for a moment.{wait}"


def confirm_enrolment(user, token):
    """Arm the device, but only if the user can already generate a valid code."""
    device = get_device(user, confirmed=False)
    if not device:
        return False, "Start the setup again - there is no pending device for this account."

    throttled = _throttle_message(device)
    if throttled:
        return False, throttled

    if not device.verify_token(str(token or "").strip()):
        return False, "That code is not right. Check your authenticator app and try again."

    # Replace any previously confirmed device, so re-enrolling works cleanly.
    TOTPDevice.objects.filter(user=user, confirmed=True).exclude(pk=device.pk).delete()
    device.confirmed = True
    device.save(update_fields=["confirmed"])
    return True, "Two-factor authentication is now on for this account."


def verify(user, token):
    """Check a login code. Returns (ok, message-or-None).

    The message matters: django-otp locks a device after failed attempts, and
    telling someone "wrong code" when the real answer is "wait two seconds"
    sends them off resetting an authenticator that was working fine.
    """
    device = get_device(user, confirmed=True)
    if not device:
        return False, None

    throttled = _throttle_message(device)
    if throttled:
        return False, throttled

    # django-otp handles the time window and refuses a replayed code.
    if device.verify_token(str(token or "").strip()):
        return True, None
    return False, None


def disable(user):
    return TOTPDevice.objects.filter(user=user).delete()[0]
