from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DepartmentViewSet, EquipmentTypeViewSet, GateViewSet, RulesView

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("gates", GateViewSet, basename="gate")
router.register("equipment-types", EquipmentTypeViewSet, basename="equipment-type")

urlpatterns = [
    # Not a viewset: the rules are a flat map of key to value, not a
    # collection of records, and pretending otherwise would give the screen a
    # list of rows to page through instead of a settings form.
    path("rules/", RulesView.as_view(), name="rules"),
    path("", include(router.urls)),
]
