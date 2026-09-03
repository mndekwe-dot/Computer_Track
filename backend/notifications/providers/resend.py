"""Email through Resend.

A Django email backend rather than something the outbox calls directly, so
everything that already sends mail - the audit alert, a password reset added
later, `send_mail` from a management command - goes through Resend without
knowing about it.

Resend's API takes one message per call. `send_messages` therefore loops, and
returns the number that were accepted rather than raising on the first
failure: a batch where three of four addresses are good should deliver three.
The outbox records the failure for the fourth and retries only that one.
"""

import json
import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class ResendError(RuntimeError):
    """A message Resend refused. Carries whether retrying could ever help."""

    def __init__(self, message, status_code=None, permanent=False):
        super().__init__(message)
        self.status_code = status_code
        self.permanent = permanent


def _post(url, payload, api_key, timeout):
    """The one place this module touches the network.

    Split out so tests can replace it. Everything above it is logic worth
    testing and none of it needs a socket.
    """
    return requests.post(
        url,
        data=json.dumps(payload),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=timeout,
    )


def _addresses(values):
    return [str(value) for value in values if value]


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = getattr(settings, "RESEND_API_KEY", "")
        self.url = getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails")
        self.timeout = getattr(settings, "RESEND_TIMEOUT", 15)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        if not self.api_key:
            # Refused loudly rather than dropped quietly. A university that
            # has switched mail on and sees nothing arrive needs to be told
            # the key is missing, not left guessing at spam filters.
            message = (
                "RESEND_API_KEY is not set, so no email can be sent. Set it, or set "
                "EMAIL_PROVIDER=console while you are working locally."
            )
            if self.fail_silently:
                logger.error(message)
                return 0
            raise ResendError(message, permanent=True)

        sent = 0
        for message in email_messages:
            try:
                self._send_one(message)
                sent += 1
            except Exception:
                if not self.fail_silently:
                    raise
                logger.exception("Resend refused a message to %s", message.to)
        return sent

    def _payload(self, message):
        payload = {
            "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
            "to": _addresses(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        if message.cc:
            payload["cc"] = _addresses(message.cc)
        if message.bcc:
            payload["bcc"] = _addresses(message.bcc)
        if message.reply_to:
            payload["reply_to"] = _addresses(message.reply_to)

        # An HTML alternative when the caller attached one. Plain text is
        # always sent as well: a gate notification has to be readable in
        # whatever a student's phone opens it in.
        for content, mimetype in getattr(message, "alternatives", []) or []:
            if mimetype == "text/html":
                payload["html"] = content
        return payload

    def _send_one(self, message):
        response = _post(self.url, self._payload(message), self.api_key, self.timeout)

        if response.status_code in (200, 201, 202):
            return True

        detail = self._describe(response)
        # 4xx other than 429 means the message itself is wrong - a malformed
        # address, an unverified sending domain. Retrying changes nothing, so
        # it is marked permanent and the outbox stops after this attempt
        # rather than burning five.
        permanent = 400 <= response.status_code < 500 and response.status_code != 429
        raise ResendError(
            f"Resend returned {response.status_code}: {detail}",
            status_code=response.status_code,
            permanent=permanent,
        )

    @staticmethod
    def _describe(response):
        try:
            body = response.json()
        except ValueError:
            return (response.text or "")[:300]
        if isinstance(body, dict):
            return str(body.get("message") or body.get("error") or body)[:300]
        return str(body)[:300]
