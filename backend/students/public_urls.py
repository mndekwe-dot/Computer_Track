from django.urls import path

from .public import (
    PublicLookupChoicesView,
    PublicMissingReportView,
    PublicRegistrationView,
    PublicStatusView,
)

urlpatterns = [
    path("register-computer/", PublicRegistrationView.as_view(), name="public-register"),
    path("my-computers/", PublicStatusView.as_view(), name="public-status"),
    path("report-missing/", PublicMissingReportView.as_view(), name="public-report-missing"),
    path("choices/", PublicLookupChoicesView.as_view(), name="public-choices"),
]
