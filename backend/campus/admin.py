from django.contrib import admin

from .models import Department, EquipmentType, Gate, Rule


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty")
    search_fields = ("code", "name", "faculty")


@admin.register(Gate)
class GateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location", "is_active", "allows_entry", "allows_exit")
    list_filter = ("is_active", "allows_entry", "allows_exit")
    search_fields = ("code", "name", "location")


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ("sort_order", "code", "label", "is_active", "offered_to_students")
    list_filter = ("is_active", "offered_to_students")
    search_fields = ("code", "label")
    ordering = ("sort_order", "label")


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):
    """Present for inspection, not as the place to change policy.

    The Registration Office portal validates each value against the registry
    in campus/rules.py; this form does not, so a value typed here can be one
    the rest of the system will refuse to read and quietly fall back on.
    """

    list_display = ("key", "value", "updated_by", "updated_at")
    search_fields = ("key",)
    readonly_fields = ("updated_at",)
