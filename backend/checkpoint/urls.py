from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DashboardView, GateLookupView, ScanEventViewSet

router = DefaultRouter()
router.register("scans", ScanEventViewSet, basename="scan")

urlpatterns = [
    path("lookup/", GateLookupView.as_view(), name="gate-lookup"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("", include(router.urls)),
]
