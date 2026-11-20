"""Signed, expiring URLs for uploaded photos.

A student's face beside their registration number is the most sensitive thing
this system stores, and it used to be the least protected. Files under
MEDIA_ROOT were served straight off disk with no check at all, so anybody
holding a URL could open it forever, and URLs leak: into browser history, into
proxy logs, into a screenshot pasted in a group chat. An unguessable filename
is not authorisation.

The obvious fix, putting the files behind a login-checked view, does not work
by itself. `<img src>` cannot send an Authorization header, and this app keeps
its JWT in memory rather than in a cookie, so the browser has nothing to
present. Instead the API hands out short-lived signed URLs: a serializer signs
the file path with the project secret, the browser loads the image like any
other, and the link is worthless once it expires.

That is a tradeoff, not a perfect answer. Anyone who copies a URL out of the
page can share it until it expires. MEDIA_LINK_TTL_SECONDS is how long you are
willing for that to be true. It is still a large improvement on a URL that
worked forever and was never checked at all.
"""

from pathlib import Path

from django.conf import settings
from django.core import signing
from django.http import FileResponse, Http404, HttpResponse
from django.urls import reverse
from django.views import View
from rest_framework import serializers

SALT = "etracker.media"

# Only these are ever served, and only with the type stated here. Anything
# else is refused rather than guessed at. An uploads directory that will
# render whatever content type it infers is a stored-XSS hole waiting for the
# first .svg or .html that slips past validation, and SVG in particular is a
# script-carrying document that browsers are happy to execute.
INLINE_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def link_ttl():
    return int(getattr(settings, "MEDIA_LINK_TTL_SECONDS", 900))


def sign_media_name(name):
    """Sign a path relative to MEDIA_ROOT into a URL-safe token.

    `signing.dumps` base64s the payload, so the result never contains a slash
    and drops into a single URL path segment unescaped.
    """
    return signing.dumps(str(name), salt=SALT, compress=True)


def signed_media_url(fieldfile):
    """Signed URL for a FileField value, or None when there is no file."""
    if not fieldfile:
        return None
    name = getattr(fieldfile, "name", None) or str(fieldfile)
    if not name:
        return None
    return reverse("protected-media", args=[sign_media_name(name)])


def resolve_within_media_root(name):
    """Absolute path for `name`, or None if it escapes MEDIA_ROOT.

    The name came out of a signature this project issued, so this is defence
    in depth rather than the main guard. It stays because the cost of being
    wrong is reading any file the process can reach, and the check is cheap.
    """
    root = Path(settings.MEDIA_ROOT).resolve()
    try:
        candidate = (root / name).resolve()
    except (OSError, ValueError):
        return None
    if root not in candidate.parents:
        return None
    return candidate


class ProtectedMediaView(View):
    """Serve one uploaded file, and only against a signature we issued."""

    def get(self, request, token):
        try:
            name = signing.loads(token, salt=SALT, max_age=link_ttl())
        except signing.SignatureExpired:
            # Distinguished from a bad signature on purpose. Expiry is the
            # normal case for a page left open over a lunch break, and
            # "reload" is a fix the person can actually carry out.
            return HttpResponse(
                "This image link has expired. Reload the page to view it again.",
                status=410,
                content_type="text/plain",
            )
        except signing.BadSignature:
            raise Http404

        path = resolve_within_media_root(name)
        if path is None:
            raise Http404

        content_type = INLINE_TYPES.get(path.suffix.lower())
        if content_type is None:
            raise Http404

        if getattr(settings, "MEDIA_ACCEL_REDIRECT", False):
            # nginx does the sending. Django still did the signature check,
            # but never touches the file, so a gate console loading photos
            # does not tie up a worker.
            response = HttpResponse(content_type=content_type)
            prefix = getattr(settings, "MEDIA_ACCEL_PREFIX", "/protected-media/")
            response["X-Accel-Redirect"] = f"{prefix.rstrip('/')}/{name}"
        else:
            if not path.is_file():
                raise Http404
            response = FileResponse(path.open("rb"), content_type=content_type)

        response["Content-Disposition"] = "inline"
        # The type above is asserted, never sniffed.
        response["X-Content-Type-Options"] = "nosniff"
        # Private, so a shared proxy never holds a student's photo, but
        # cacheable in the one browser that asked, so scrolling a table of
        # results does not refetch every face.
        response["Cache-Control"] = f"private, max-age={link_ttl()}"
        return response


class SignedImageField(serializers.ImageField):
    """Accepts an upload like any ImageField, renders as a signed URL."""

    def to_representation(self, value):
        return signed_media_url(value)
