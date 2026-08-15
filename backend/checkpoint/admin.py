from django.contrib import admin

from .models import ScanEvent


@admin.register(ScanEvent)
class ScanEventAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "gate",
        "direction",
        "verdict",
        "claimed_reg_number",
        "device_label",
        "guard",
    )
    list_filter = ("verdict", "direction", "gate", "method")
    search_fields = ("claimed_serial", "claimed_reg_number", "student_name", "device_label")
    date_hierarchy = "created_at"

    def has_change_permission(self, request, obj=None):
        # The gate log is evidence; it must not be editable after the fact.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
