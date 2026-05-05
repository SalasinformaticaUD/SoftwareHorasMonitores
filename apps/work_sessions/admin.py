from django.contrib import admin

from apps.work_sessions.models import WorkSession


@admin.register(WorkSession)
class WorkSessionAdmin(admin.ModelAdmin):
    list_display = (
        "monitor",
        "work_day",
        "normal_minutes",
        "overtime_minutes",
        "overtime_status",
        "is_late",
    )
    list_filter = ("overtime_status", "is_late", "monitor__department")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante")

