from django.contrib import admin

from apps.reports.models import MonitorMemorandum, MonitorReportSnapshot


@admin.register(MonitorReportSnapshot)
class MonitorReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("monitor", "start_date", "end_date", "total_minutes", "has_memorandum")
    list_filter = ("department", "has_memorandum")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante")


@admin.register(MonitorMemorandum)
class MonitorMemorandumAdmin(admin.ModelAdmin):
    list_display = ("monitor", "late_count_threshold", "sent_to", "sent_at", "created_at")
    list_filter = ("sent_at", "late_count_threshold")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante", "sent_to")
    readonly_fields = ("created_at", "updated_at", "sent_at")

