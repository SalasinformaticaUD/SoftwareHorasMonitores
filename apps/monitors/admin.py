from django.contrib import admin

from apps.monitors.models import Monitor


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

