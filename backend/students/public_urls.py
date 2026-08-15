from django.urls import path

from .public import PublicLookupChoicesView, PublicRegistrationView, PublicStatusView

urlpatterns = [
    path("register-computer/", PublicRegistrationView.as_view(), name="public-register"),
    path("my-computers/", PublicStatusView.as_view(), name="public-status"),
    path("choices/", PublicLookupChoicesView.as_view(), name="public-choices"),
]
