from django.contrib import admin

from apps.attendance.models import AttendanceImportJob, AttendanceRawRecord


@admin.register(AttendanceImportJob)
class AttendanceImportJobAdmin(admin.ModelAdmin):
    list_display = ("file_name", "status", "uploaded_by", "created_at", "imported_rows", "failed_rows")
    list_filter = ("status",)
    search_fields = ("file_name",)


@admin.register(AttendanceRawRecord)
class AttendanceRawRecordAdmin(admin.ModelAdmin):
    list_display = (
        "raw_full_name",
        "raw_department",
        "work_day",
        "reconciliation_status",
        "monitor",
        "processed_at",
    )
    list_filter = ("reconciliation_status", "raw_department")
    search_fields = ("raw_full_name", "raw_department", "monitor__full_name")

