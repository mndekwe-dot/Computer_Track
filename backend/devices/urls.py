from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DeviceFlagViewSet,
    DeviceViewSet,
    OwnershipTransferViewSet,
    TemporaryPermitViewSet,
)

router = DefaultRouter()
router.register("flags", DeviceFlagViewSet, basename="device-flag")
router.register("permits", TemporaryPermitViewSet, basename="permit")
router.register("transfers", OwnershipTransferViewSet, basename="transfer")
router.register("", DeviceViewSet, basename="device")

urlpatterns = [path("", include(router.urls))]
