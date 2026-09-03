from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DeviceFlagViewSet,
    DeviceViewSet,
    OwnershipTransferViewSet,
    RegistrationAttemptViewSet,
    TemporaryPermitViewSet,
)

router = DefaultRouter()
router.register("flags", DeviceFlagViewSet, basename="device-flag")
router.register("permits", TemporaryPermitViewSet, basename="permit")
router.register("transfers", OwnershipTransferViewSet, basename="transfer")
router.register("registration-attempts", RegistrationAttemptViewSet, basename="attempt")
# Registered last: its prefix is empty and would otherwise swallow the others.
router.register("", DeviceViewSet, basename="device")

urlpatterns = [path("", include(router.urls))]
