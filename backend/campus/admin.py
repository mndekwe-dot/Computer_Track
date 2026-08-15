from django.contrib import admin

from .models import Department, Gate


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "faculty")
    search_fields = ("code", "name", "faculty")


@admin.register(Gate)
class GateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "location", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "location")
