from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from .media import ProtectedMediaView


def health(_request):
    return JsonResponse({"status": "ok", "service": "computer-track-api"})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls")),
    # Unauthenticated student form. Kept on its own prefix so it is obvious at
    # a glance which surface is public.
    path("api/public/", include("students.public_urls")),
    path("api/campus/", include("campus.urls")),
    path("api/students/", include("students.urls")),
    path("api/devices/", include("devices.urls")),
    path("api/checkpoint/", include("checkpoint.urls")),
    path("api/search/", include("search.urls")),
    # Uploaded photos. Signed and expiring rather than served off disk: see
    # config/media.py for why an unguessable filename is not enough.
    path("api/media/<str:token>/", ProtectedMediaView.as_view(), name="protected-media"),
]

if settings.DEBUG:
    # Raw media, for the Django admin's own thumbnails and for poking at
    # uploads during development. Never mounted with DEBUG off, so the signed
    # view above is the only way in on a deployed instance.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
