from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "get_full_name", "role", "staff_number", "default_gate", "is_active")
    list_filter = ("role", "is_active", "default_gate")
    search_fields = ("username", "first_name", "last_name", "staff_number", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Gate duty", {"fields": ("role", "staff_number", "phone", "default_gate")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Gate duty", {"fields": ("role", "staff_number", "phone", "default_gate")}),
    )
