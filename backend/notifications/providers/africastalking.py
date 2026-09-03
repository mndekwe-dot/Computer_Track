"""SMS through Africa's Talking.

Written against the REST endpoint rather than the vendor SDK. The SDK is a
thin wrapper over one form post, and depending on it would mean a second
place where the sandbox and live URLs are chosen, a second timeout to
configure, and a version to keep current for no gain.

Two things this has to get right, because both cost real money or real trust:

  Numbers. Student records hold local numbers as people write them, "0788...".
  Africa's Talking accepts E.164 only, and silently does nothing useful with
  anything else. Normalisation happens here, once.

  Length. A segment is 160 characters and every segment is billed. A message
  that runs long is truncated with a pointer to the portal rather than
  quietly costing four times as much per student.
"""

import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SMSError(RuntimeError):
    def __init__(self, message, permanent=False):
        super().__init__(message)
        self.permanent = permanent


# Shortest plausible national subscriber number, and shortest plausible whole
# E.164 number. Both are deliberately loose - the aim is to catch a typo, not
# to reimplement libphonenumber.
MIN_NATIONAL_DIGITS = 7
MIN_E164_DIGITS = 8

# Statuses Africa's Talking reports per recipient. Anything outside the first
# set means the message did not go; the second set will never go, however many
# times it is retried.
ACCEPTED = {"Success", "Sent", "Queued"}
PERMANENT_FAILURES = {
    "InvalidPhoneNumber",
    "UnsupportedNumberType",
    "InsufficientBalance",
    "UserInBlacklist",
    "UserIsInactive",
    "InvalidSenderId",
}


def normalise_number(raw, country_code=None):
    """A local number as typed into E.164, or None if it cannot be one.

    Handles the four ways the same Rwandan mobile gets written on a form:
    "0788123456", "788123456", "+250788123456", "250 788 123 456".
    """
    if not raw:
        return None
    code = (country_code or getattr(settings, "SMS_DEFAULT_COUNTRY_CODE", "+250")).strip()
    if not code.startswith("+"):
        code = "+" + code
    digits_only = re.sub(r"[^\d+]", "", str(raw))
    if not digits_only:
        return None

    if digits_only.startswith("+"):
        return digits_only if len(digits_only) >= MIN_E164_DIGITS + 1 else None

    bare_code = code.lstrip("+")
    if digits_only.startswith("00"):
        candidate = "+" + digits_only[2:]
    elif digits_only.startswith(bare_code) and len(digits_only) > len(bare_code):
        candidate = "+" + digits_only
    else:
        # A national number: drop the trunk zero before prefixing the country.
        national = digits_only.lstrip("0")
        # A handful of digits is a typo, not a phone number. Prefixing a
        # country code onto it would produce something that looks valid, gets
        # sent, and is charged for.
        if len(national) < MIN_NATIONAL_DIGITS:
            return None
        candidate = code + national

    return candidate if len(candidate) >= MIN_E164_DIGITS + 1 else None


def truncate(message, limit=None):
    limit = limit or getattr(settings, "SMS_MAX_LENGTH", 320)
    text = " ".join((message or "").split())
    if len(text) <= limit:
        return text
    # Cut on a word boundary where there is one nearby, so the message does
    # not end mid-word.
    cut = text[: limit - 1]
    space = cut.rfind(" ")
    if space > limit * 0.6:
        cut = cut[:space]
    return cut.rstrip(" .,;:") + "…"


def _post(url, data, api_key, timeout):
    """The only network call. Replaced wholesale in tests."""
    return requests.post(
        url,
        data=data,
        headers={
            "apiKey": api_key,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        timeout=timeout,
    )


class AfricasTalkingSMSBackend:
    def __init__(self):
        self.username = getattr(settings, "AFRICASTALKING_USERNAME", "sandbox")
        self.api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
        self.sender_id = getattr(settings, "AFRICASTALKING_SENDER_ID", "")
        self.timeout = getattr(settings, "AFRICASTALKING_TIMEOUT", 15)
        # "sandbox" is the literal username Africa's Talking issues for the
        # test environment, and it only works against the sandbox host.
        # Choosing the URL from the username rather than a separate flag
        # removes the configuration that can contradict itself.
        if self.username == "sandbox":
            self.url = getattr(
                settings,
                "AFRICASTALKING_SANDBOX_API_URL",
                "https://api.sandbox.africastalking.com/version1/messaging",
            )
        else:
            self.url = getattr(
                settings,
                "AFRICASTALKING_API_URL",
                "https://api.africastalking.com/version1/messaging",
            )

    def send(self, to, message):
        """True when the provider accepted it. Raises when it should be retried."""
        if not self.api_key:
            raise SMSError(
                "AFRICASTALKING_API_KEY is not set, so no SMS can be sent. Set it, or set "
                "SMS_PROVIDER=console while you are working locally.",
                permanent=True,
            )

        number = normalise_number(to)
        if not number:
            # Not retryable, and not an error worth waking anyone for: the
            # student's record simply has no usable number on it.
            logger.warning("Cannot send SMS: %r is not a usable phone number", to)
            raise SMSError(f"{to!r} is not a usable phone number", permanent=True)

        data = {
            "username": self.username,
            "to": number,
            "message": truncate(message),
        }
        if self.sender_id:
            data["from"] = self.sender_id

        response = _post(self.url, data, self.api_key, self.timeout)
        if response.status_code not in (200, 201):
            raise SMSError(
                f"Africa's Talking returned {response.status_code}: {(response.text or '')[:300]}",
                permanent=400 <= response.status_code < 500 and response.status_code != 429,
            )

        return self._check_recipients(response, number)

    @staticmethod
    def _check_recipients(response, number):
        """A 200 does not mean it was sent.

        Africa's Talking answers 200 with a per-recipient status, so a
        malformed number or an empty account looks like success at the HTTP
        layer. The recipient list is where the truth is.
        """
        try:
            body = response.json()
        except ValueError:
            raise SMSError("Africa's Talking returned a response that was not JSON")

        recipients = (body.get("SMSMessageData") or {}).get("Recipients") or []
        if not recipients:
            detail = (body.get("SMSMessageData") or {}).get("Message") or body
            raise SMSError(f"Africa's Talking accepted no recipients: {str(detail)[:300]}")

        first = recipients[0]
        status = first.get("status") or first.get("statusCode")
        if status in ACCEPTED:
            return True
        raise SMSError(
            f"Africa's Talking rejected {number}: {status}",
            permanent=status in PERMANENT_FAILURES,
        )
