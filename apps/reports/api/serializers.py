from rest_framework import serializers

from apps.reports.models import MonitorReportSnapshot


class MonitorReportSnapshotSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)
    remaining_minutes = serializers.SerializerMethodField()

    class Meta:
        model = MonitorReportSnapshot
        fields = (
            "id",
            "monitor",
            "monitor_name",
            "department",
            "start_date",
            "end_date",
            "normal_minutes",
            "approved_overtime_minutes",
            "pending_overtime_minutes",
            "penalty_minutes",
            "late_count",
            "annotation_delta_minutes",
            "total_minutes",
            "remaining_minutes",
            "has_memorandum",
            "created_at",
        )

    def get_remaining_minutes(self, obj):
        target_minutes = 192 * 60
        completed_minutes = (
            obj.normal_minutes
            + obj.approved_overtime_minutes
            + obj.annotation_delta_minutes
        )
        return max(target_minutes - completed_minutes, 0)


class GenerateReportSerializer(serializers.Serializer):
    monitor_id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
