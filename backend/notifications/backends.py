"""Handing one message to whichever provider is configured.

The providers themselves live in notifications/providers/. This module only
picks one and reports what happened, in the two terms the outbox cares about:
did it go, and is it worth trying again.

That second question is the whole reason this file is not two lines. A mail
server that is down for a minute and an address that does not exist both fail
the same way to a naive caller, and treating them the same means either
retrying a dead address five times or giving up on a working one. Providers
raise errors carrying `permanent`; everything else is assumed retryable,
because assuming the safer of the two is what keeps a real message from being
dropped on a temporary fault.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage, get_connection
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class PermanentFailure(RuntimeError):
    """This message will never send. Stop retrying it."""


def get_sms_backend():
    path = getattr(settings, "SMS_BACKEND", None)
    if not path:
        from .providers.console import NullSMSBackend

        return NullSMSBackend()
    try:
        return import_string(path)()
    except ImportError:
        # A misconfigured provider must not take the gate down with it. The
        # null backend refuses to send, the outbox records the refusal, and
        # the log says exactly what to fix.
        logger.exception("SMS_BACKEND %r could not be imported; falling back to null", path)
        from .providers.console import NullSMSBackend

        return NullSMSBackend()


def _is_permanent(error):
    return bool(getattr(error, "permanent", False))


def deliver(notification):
    """Send one notification.

    Returns True on success. Raises on failure - `PermanentFailure` when
    retrying is pointless, anything else when it is worth another go.
    """
    from .models import Channel

    if notification.channel == Channel.EMAIL:
        return _deliver_email(notification)

    if notification.channel == Channel.SMS:
        return _deliver_sms(notification)

    raise PermanentFailure(f"Unknown channel {notification.channel!r}")


def _deliver_email(notification):
    message = EmailMessage(
        subject=notification.subject,
        body=notification.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[notification.recipient],
        connection=get_connection(fail_silently=False),
    )
    try:
        sent = message.send(fail_silently=False)
    except Exception as error:
        if _is_permanent(error):
            raise PermanentFailure(str(error)) from error
        raise
    if not sent:
        raise RuntimeError("The mail backend accepted nothing and reported no error")
    return True


def _deliver_sms(notification):
    backend = get_sms_backend()
    try:
        accepted = backend.send(notification.recipient, notification.body)
    except Exception as error:
        if _is_permanent(error):
            raise PermanentFailure(str(error)) from error
        raise
    if not accepted:
        # A backend that declines without raising - the null backend, or a
        # provider that answered "no" cleanly. Nothing to retry.
        raise PermanentFailure("The SMS backend declined to send")
    return True
