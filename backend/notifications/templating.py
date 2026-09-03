"""The words that get sent, and who owns them.

Every message this system sends used to be an f-string in service.py, which
meant a university could not change "Good news" to something more formal, or
translate anything, or add their own telephone number, without a developer and
a release. The text lives in a table now and is edited in the Registration
Office portal.

Three things make that safe to hand over:

  A missing placeholder never raises. A registrar who deletes `{serial}` from
  the approval email gets an email without a serial number, not a 500 on the
  approve button.

  An unknown placeholder is left as written rather than blanked, so a typo is
  visible in the sent message and gets reported, instead of vanishing.

  A blank or missing template falls back to the default below. The system
  cannot be left unable to warn somebody that their laptop just left campus.
"""

import logging
import string

from django.conf import settings

from config import requestcache
from config.cache import derived

logger = logging.getLogger(__name__)

CACHE_KEY = "notifications.templates.v1"


class _Safe(dict):
    """Leaves `{unknown}` alone instead of raising KeyError."""

    def __missing__(self, key):
        return "{" + key + "}"


def render(text, context):
    """Fill placeholders, surviving anything a person might type.

    `string.Formatter().vformat` rather than str.format so a stray brace - a
    smiley, a JSON snippet somebody pasted - degrades to leaving the text
    alone rather than raising in the middle of sending.
    """
    if not text:
        return ""
    try:
        return string.Formatter().vformat(text, (), _Safe(context))
    except (ValueError, IndexError, TypeError):
        logger.warning("Notification template has unbalanced braces; sent unrendered")
        return text


# What each kind of message may refer to. Shown beside the editor, because a
# registrar cannot guess `{gate}` and should not have to.
PLACEHOLDERS = {
    "EXIT": ["student_first_name", "student_name", "device", "serial", "gate", "time", "university"],
    "APPROVED": ["student_first_name", "student_name", "device", "serial", "asset_tag", "university", "office"],
    "REJECTED": ["student_first_name", "student_name", "device", "serial", "reason", "university", "office"],
    "MISSING": ["student_first_name", "student_name", "device", "serial", "report", "university", "office", "security_phone"],
    "SUSPICIOUS": ["serial", "brand", "reason", "reg_number", "university"],
    "AUDIT_ALERT": ["university"],
}

# The starting text. Seeded into the table on migration, and used if a row is
# ever missing or blank.
DEFAULTS = {
    ("EXIT", "EMAIL"): (
        "Your computer just left campus",
        "{student_first_name},\n\n"
        "Your computer ({device}, serial {serial}) was recorded leaving {university} through "
        "{gate} at {time}.\n\n"
        "If this was not you, contact campus security immediately.\n",
    ),
    ("EXIT", "SMS"): (
        "",
        "{device} ({serial}) left {university} via {gate} at {time}. Not you? Call security now.",
    ),
    ("APPROVED", "EMAIL"): (
        "Your computer registration was approved",
        "{student_first_name},\n\n"
        "Your {device} (serial {serial}) has been approved and is now on the {university} "
        "computer register.{asset_tag}\n\n"
        "You may carry it through any gate. Collect its QR sticker from {office} if you have "
        "not already.\n",
    ),
    ("APPROVED", "SMS"): (
        "",
        "{device} ({serial}) is approved and on the {university} register. You may carry it "
        "through any gate.",
    ),
    ("REJECTED", "EMAIL"): (
        "Your computer registration needs attention",
        "{student_first_name},\n\n"
        "Your registration for {device} (serial {serial}) was not approved.\n\n"
        "Reason: {reason}\n\n"
        "Please visit {office} with the computer to sort this out. Until it is registered, it "
        "will be held at the gate.\n",
    ),
    ("REJECTED", "SMS"): (
        "",
        "Registration for {device} ({serial}) was not approved: {reason}. Please visit {office}.",
    ),
    ("MISSING", "EMAIL"): (
        "{report}: {device}",
        "{student_first_name},\n\n"
        "{device} (serial {serial}) has been reported {report} using the public form on the "
        "{university} computer register.\n\n"
        "Every gate on campus will now stop this computer.\n\n"
        "If you did not make this report, take your student ID to {office} and they will lift "
        "the hold.\n",
    ),
    ("MISSING", "SMS"): (
        "",
        "{device} ({serial}) was reported {report}. Every gate will now stop it. Not you? "
        "Go to {office} with your student ID.",
    ),
}


def _rows():
    return requestcache.get(CACHE_KEY, _load_rows)


def _load_rows():
    rows = derived().get(CACHE_KEY)
    if rows is None:
        from .models import NotificationTemplate

        rows = {
            (row["kind"], row["channel"]): (row["subject"], row["body"])
            for row in NotificationTemplate.objects.filter(is_active=True).values(
                "kind", "channel", "subject", "body"
            )
        }
        derived().set(CACHE_KEY, rows, getattr(settings, "CACHE_TIMEOUT_RULES", 600))
    return rows


def template_for(kind, channel):
    """The stored template, or the default when there is not a usable one."""
    stored = _rows().get((kind, channel))
    if stored and (stored[1] or "").strip():
        return stored
    return DEFAULTS.get((kind, channel), ("", ""))


def compose(kind, channel, context):
    """(subject, body) ready to send."""
    subject, body = template_for(kind, channel)
    return render(subject, context), render(body, context)


def invalidate():
    derived().delete(CACHE_KEY)
    requestcache.clear(CACHE_KEY)
