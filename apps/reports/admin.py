from django.contrib import admin

from apps.reports.models import MonitorReportSnapshot


@admin.register(MonitorReportSnapshot)
class MonitorReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("monitor", "start_date", "end_date", "total_minutes", "has_memorandum")
    list_filter = ("department", "has_memorandum")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante")

