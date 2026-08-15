from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AccessLogViewSet,
    ChangePasswordView,
    LoginView,
    MeView,
    TwoFactorView,
    UserViewSet,
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("access-log", AccessLogViewSet, basename="access-log")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("me/", MeView.as_view(), name="me"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("two-factor/", TwoFactorView.as_view(), name="two-factor"),
    path("", include(router.urls)),
]
