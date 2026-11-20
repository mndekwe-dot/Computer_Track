from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from .media import ProtectedMediaView


def health(_request):
    """Liveness for the load balancer and the container healthcheck.

    Deliberately does not touch the database. A health check that fails when
    Postgres is slow takes the whole service out of the pool at exactly the
    moment it is struggling, which turns a slow minute into an outage.
    """
    return JsonResponse({"status": "ok", "service": "etracker-api"})


def ready(_request):
    """Readiness: can this instance actually serve a request?

    This one *does* touch the database and the cache, because an instance that
    cannot reach either should not be sent traffic. Used by the container
    healthcheck and by a deployment waiting to cut over.
    """
    from django.core.cache import cache
    from django.db import connection

    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as error:
        checks["database"] = f"failed: {error.__class__.__name__}"

    try:
        cache.set("readiness", "ok", 5)
        checks["cache"] = "ok" if cache.get("readiness") == "ok" else "failed: no round trip"
    except Exception as error:
        checks["cache"] = f"failed: {error.__class__.__name__}"

    healthy = all(value == "ok" for value in checks.values())
    return JsonResponse({"status": "ok" if healthy else "degraded", "checks": checks},
                        status=200 if healthy else 503)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/ready/", ready, name="ready"),
    path("api/auth/", include("accounts.urls")),
    # Unauthenticated student form. Kept on its own prefix so it is obvious at
    # a glance which surface is public.
    path("api/public/", include("students.public_urls")),
    path("api/campus/", include("campus.urls")),
    path("api/students/", include("students.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/checkpoint/", include("checkpoint.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/search/", include("search.urls")),
    # Uploaded photos. Signed and expiring rather than served off disk: see
    # config/media.py for why an unguessable filename is not enough.
    path("api/media/<str:token>/", ProtectedMediaView.as_view(), name="protected-media"),
]

# Errors as JSON, for requests that never reach a DRF view - a mistyped URL,
# a failure in middleware. Without these Django answers with an HTML page,
# which a fetch() reads as unparseable noise and the console reports as a
# meaningless failure. See config/errors.py.
handler400 = "config.errors.bad_request"
handler403 = "config.errors.permission_denied"
handler404 = "config.errors.not_found"
handler500 = "config.errors.server_error"

if settings.DEBUG:
    # Raw media, for the Django admin's own thumbnails and for poking at
    # uploads during development. Never mounted with DEBUG off, so the signed
    # view above is the only way in on a deployed instance.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
