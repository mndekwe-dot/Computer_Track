from django.contrib import admin

from .models import Device, DeviceFlag, OwnershipTransfer, TemporaryPermit


class DeviceFlagInline(admin.TabularInline):
    model = DeviceFlag
    extra = 0
    fields = ("reason", "details", "is_active", "created_at")
    readonly_fields = ("created_at",)


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("serial_number", "brand", "model_name", "owner", "status", "is_archived")
    list_filter = ("status", "device_type", "is_archived")
    search_fields = ("serial_number", "serial_key", "asset_tag", "brand", "owner__reg_number")
    readonly_fields = ("uid", "serial_key", "registered_at", "updated_at")
    inlines = (DeviceFlagInline,)
    autocomplete_fields = ("owner",)


@admin.register(DeviceFlag)
class DeviceFlagAdmin(admin.ModelAdmin):
    list_display = ("device", "reason", "is_active", "created_at", "resolved_at")
    list_filter = ("reason", "is_active")
    search_fields = ("device__serial_number", "details")


@admin.register(TemporaryPermit)
class TemporaryPermitAdmin(admin.ModelAdmin):
    list_display = ("device", "bearer_name", "valid_from", "valid_to", "is_revoked")
    list_filter = ("is_revoked",)
    search_fields = ("bearer_name", "bearer_id_number", "device__serial_number")


@admin.register(OwnershipTransfer)
class OwnershipTransferAdmin(admin.ModelAdmin):
    list_display = ("device", "from_student", "to_student", "created_at")
    search_fields = ("device__serial_number",)
