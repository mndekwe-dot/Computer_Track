"""Delivery channels. Email is real; SMS is an interface awaiting a provider."""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class ConsoleSMSBackend:
    """Logs instead of sending. The default, so nothing silently costs money."""

    def send(self, to, message):
        logger.info("SMS to %s: %s", to, message)
        return True


class NullSMSBackend:
    """Sends nothing at all. For tests and deployments without SMS."""

    def send(self, to, message):
        return False


def get_sms_backend():
    path = getattr(settings, "SMS_BACKEND", None)
    if not path:
        return NullSMSBackend()
    try:
        return import_string(path)()
    except ImportError:
        logger.exception("SMS_BACKEND %r could not be imported; falling back to null", path)
        return NullSMSBackend()


def deliver(notification):
    """Send one notification. Raises on failure so the caller can retry."""
    from .models import Channel

    if notification.channel == Channel.EMAIL:
        send_mail(
            subject=notification.subject,
            message=notification.body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient],
            fail_silently=False,
        )
        return True

    if notification.channel == Channel.SMS:
        if not get_sms_backend().send(notification.recipient, notification.body):
            raise RuntimeError("SMS backend declined to send")
        return True

    raise ValueError(f"Unknown channel {notification.channel!r}")
