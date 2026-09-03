"""One error shape, for every failure the API can produce.

The frontend already knew how to read DRF's `{"field": ["message"]}` and its
`{"detail": "..."}`. What it could not read was the two cases DRF does not
handle: an unexpected exception, which arrived as an HTML debug page or an
empty 500, and a 404 on a URL that is not an API route at all. Both surfaced
in the console as "Request failed with 500", which names nothing a person can
do about it.

So every response from here carries the same three things:

  detail   - one sentence a person can act on
  code     - a stable string for the client to branch on, never shown
  errors   - per-field messages, when the failure was per-field

Nothing here leaks internals. A database error says a database error
happened; the traceback goes to the log, where the person who can read it is.
"""

import logging
import uuid

from django.core.signals import got_request_exception
from django.http import JsonResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)

# What a person is told, per status. The wording matters more than it looks:
# each one has to end in something the reader can actually do next.
MESSAGES = {
    400: "Some of what was entered could not be accepted. The details are on the form.",
    401: "Your session has expired. Sign in again to continue.",
    403: "This account does not have permission to do that.",
    404: "That record no longer exists. It may have been removed since the page loaded.",
    405: "That action is not available here.",
    409: "Somebody else changed this record first. Reload the page and try again.",
    413: "That file is too large. Choose a smaller photograph.",
    415: "That kind of file cannot be uploaded here.",
    429: "Too many requests. Wait a moment, then try again.",
    500: "Something went wrong at our end. Try again, and tell IT if it keeps happening.",
    502: "The server is not reachable right now. Try again in a moment.",
    503: "The service is temporarily unavailable. Try again in a moment.",
}

CODES = {
    400: "invalid",
    401: "not_authenticated",
    403: "permission_denied",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "too_large",
    415: "unsupported_media_type",
    429: "throttled",
    500: "server_error",
    502: "bad_gateway",
    503: "unavailable",
}


def _message_for(code):
    return MESSAGES.get(code, MESSAGES[500] if code >= 500 else MESSAGES[400])


def _envelope(status_code, detail=None, errors=None, code=None, **extra):
    body = {
        "detail": detail or _message_for(status_code),
        "code": code or CODES.get(status_code, "error"),
    }
    if errors:
        body["errors"] = errors
    body.update(extra)
    return body


def api_exception_handler(exc, context):
    """DRF's handler, plus the cases it deliberately declines to handle."""
    response = drf_exception_handler(exc, context)

    if response is None:
        # Not an APIException: a bug, a database error, something unforeseen.
        # The reference is the thread that ties what the user was told to what
        # the log recorded, without putting a traceback on their screen.
        reference = uuid.uuid4().hex[:12]
        request = context.get("request")
        logger.exception(
            "Unhandled exception [%s] on %s", reference, getattr(request, "path", "?")
        )

        # Answering with a response here means Django's own handler never
        # runs, and `got_request_exception` is what that handler would have
        # sent. Two things listen for it and both matter: error reporting in
        # production, and the test client, which re-raises so that a genuine
        # bug fails a test loudly instead of passing as "a 500 was returned".
        got_request_exception.send(sender=None, request=request)

        return Response(
            _envelope(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Something went wrong at our end and the action was not completed. "
                    f"Try again. If it keeps happening, quote reference {reference} to IT."
                ),
                reference=reference,
            ),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    data = response.data
    code = response.status_code

    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        # DRF's own single-message shape. Keep the message: it is usually more
        # specific than anything generic here would be.
        response.data = _envelope(code, detail=str(data["detail"]))
    elif isinstance(data, dict):
        # Per-field validation errors. `detail` summarises them, `errors` is
        # the flattened map a form pins to individual inputs.
        #
        # The original per-field keys stay at the top level as well. That is
        # not tidiness, it is compatibility: DRF's `{"serial_number": [...]}`
        # is what every existing client and test reads, and quietly moving it
        # one level down would break each of them for a cosmetic gain.
        errors = {
            field: " ".join(str(item) for item in value) if isinstance(value, list) else str(value)
            for field, value in data.items()
        }
        detail = errors.get("non_field_errors") or _message_for(code)
        body = _envelope(code, detail=detail, errors=errors)
        body.update(data)
        response.data = body
    elif isinstance(data, list):
        response.data = _envelope(code, detail=" ".join(str(item) for item in data))

    if code == status.HTTP_429_TOO_MANY_REQUESTS:
        # `Retry-After` is already set by DRF. Repeating it in the body lets
        # the browser say "try again in 40 seconds" instead of "try again",
        # which is the difference between waiting and refreshing in a loop.
        wait = response.headers.get("Retry-After")
        if wait:
            response.data["retry_after"] = int(wait)
            response.data["detail"] = (
                f"Too many requests from this account. Wait {wait} seconds, then try again."
            )

    return response


# ------------------------------------------------------- non-DRF responses
#
# Wired up in config/urls.py. These catch requests that never reach a DRF
# view: a mistyped URL, a failure during middleware. Without them Django
# answers with an HTML page, which a fetch() reads as unparseable noise.


def not_found(request, exception=None):
    return JsonResponse(
        _envelope(404, detail=f"No API endpoint at {request.path}", code="no_such_endpoint"),
        status=404,
    )


def server_error(request):
    return JsonResponse(_envelope(500), status=500)


def permission_denied(request, exception=None):
    return JsonResponse(_envelope(403), status=403)


def bad_request(request, exception=None):
    return JsonResponse(_envelope(400), status=400)
