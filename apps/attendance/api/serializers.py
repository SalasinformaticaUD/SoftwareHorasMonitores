from rest_framework import serializers

from apps.attendance.models import AttendanceImportJob, AttendanceRawRecord


class AttendanceImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceImportJob
        fields = (
            "id",
            "file_name",
            "source_file",
            "status",
            "total_rows",
            "imported_rows",
            "failed_rows",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )
        read_only_fields = (
            "status",
            "total_rows",
            "imported_rows",
            "failed_rows",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )


class AttendanceRawRecordSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)

    class Meta:
        model = AttendanceRawRecord
        fields = (
            "id",
            "import_job",
            "row_number",
            "raw_full_name",
            "raw_department",
            "work_day",
            "entry_at",
            "exit_at",
            "monitor",
            "monitor_name",
            "reconciliation_status",
            "manual_review_reason",
            "processed_at",
            "processing_error",
        )
        read_only_fields = fields


class ManualAssignmentSerializer(serializers.Serializer):
    monitor_id = serializers.UUIDField()

