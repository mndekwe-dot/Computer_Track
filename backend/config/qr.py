"""The QR sticker payload format.

Written into every sticker and read back at the gate, so both halves have to
agree. It is one module rather than two constants because they drifted apart
once already: the scanner half carried the colon and the printer half did not.

The prefix is configurable because a campus that already uses QR codes for
something else needs its own namespace, and because a scanner should be able
to tell one of our stickers from a random barcode on a laptop lid without
trying to parse it first.
"""

from django.conf import settings


def prefix():
    return getattr(settings, "QR_PAYLOAD_PREFIX", "CTRACK")


def build_qr_payload(device):
    """What gets encoded in the printed sticker."""
    return f"{prefix()}:{device.uid}"


def strip_prefix(query):
    """The bare identifier from a scanned payload, or the query untouched."""
    marker = f"{prefix()}:"
    text = (query or "").strip()
    if text.upper().startswith(marker.upper()):
        return text[len(marker):]
    return text
