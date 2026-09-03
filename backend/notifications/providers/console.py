"""The two providers that cost nothing and send nothing."""

import logging

logger = logging.getLogger(__name__)


class ConsoleSMSBackend:
    """Logs instead of sending. The default, so nothing silently costs money.

    SMS is the one channel here that bills per message, which makes an
    accidentally live default worse than an accidentally inert one. A
    developer who sees the log line knows the plumbing works; a developer who
    sees nothing goes looking. Neither has spent anything.
    """

    def send(self, to, message):
        logger.info("SMS to %s: %s", to, message)
        return True


class NullSMSBackend:
    """Sends nothing and says so. For tests, and for a campus without SMS."""

    def send(self, to, message):
        return False
