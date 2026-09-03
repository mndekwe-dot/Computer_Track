from django.contrib import admin

from .models import Notification, NotificationTemplate


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ("kind", "channel", "subject", "is_active", "updated_at")
    list_filter = ("kind", "channel", "is_active")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Read-only. The outbox is a record of what was sent, and a record that
    can be edited after the fact is worse than none."""

    list_display = ("created_at", "kind", "channel", "recipient", "status", "attempts")
    list_filter = ("status", "channel", "kind")
    search_fields = ("recipient", "subject", "body")
    readonly_fields = [field.name for field in Notification._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
