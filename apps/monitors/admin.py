from django.contrib import admin

from apps.monitors.models import AcademicSemester, Monitor


@admin.register(AcademicSemester)
class AcademicSemesterAdmin(admin.ModelAdmin):
    list_display = ("name", "starts_on", "ends_on", "is_active", "archived_at")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Monitor)
class MonitorAdmin(admin.ModelAdmin):
    list_display = (
        "codigo_estudiante",
        "numero_documento",
        "full_name",
        "proyecto_curricular",
        "telefono",
        "user",
        "department",
        "is_active",
    )
    list_filter = ("department", "is_active")
    search_fields = (
        "codigo_estudiante",
        "numero_documento",
        "full_name",
        "proyecto_curricular",
        "telefono",
        "user__email",
    )
