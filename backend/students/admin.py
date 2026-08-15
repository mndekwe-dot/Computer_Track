from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("reg_number", "full_name", "department", "year_of_study", "status")
    list_filter = ("status", "department", "year_of_study")
    search_fields = ("reg_number", "reg_number_key", "first_name", "last_name", "email")
    readonly_fields = ("reg_number_key", "created_at", "updated_at")
