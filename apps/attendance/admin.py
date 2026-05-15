from django.contrib import admin

from apps.attendance.models import (
    AttendanceImportJob,
    AttendanceInconsistency,
    AttendanceInconsistencyEvent,
    AttendanceRawRecord,
)


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
        "event_at",
        "pairing_status",
        "reconciliation_status",
        "monitor",
        "processed_at",
    )
    list_filter = ("reconciliation_status", "pairing_status", "raw_department", "record_type", "operation")
    search_fields = ("raw_full_name", "raw_department", "raw_user_number", "raw_user_id", "monitor__full_name")


@admin.register(AttendanceInconsistency)
class AttendanceInconsistencyAdmin(admin.ModelAdmin):
    list_display = (
        "raw_record",
        "monitor",
        "work_day",
        "inconsistency_type",
        "status",
        "solution_annotation",
        "detected_at",
    )
    list_filter = ("status", "inconsistency_type", "monitor__department")
    search_fields = ("raw_record__raw_full_name", "monitor__full_name", "message", "resolution_note")


@admin.register(AttendanceInconsistencyEvent)
class AttendanceInconsistencyEventAdmin(admin.ModelAdmin):
    list_display = ("inconsistency", "action", "actor", "created_at")
    list_filter = ("action",)
    search_fields = ("inconsistency__raw_record__raw_full_name", "note", "actor__username")

