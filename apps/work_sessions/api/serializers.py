from rest_framework import serializers

from apps.work_sessions.models import WorkSession


class WorkSessionSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)
    lateness_exception_name = serializers.CharField(source="lateness_exception.name", read_only=True)
    overtime_exception_name = serializers.CharField(source="overtime_exception.name", read_only=True)

    class Meta:
        model = WorkSession
        fields = (
            "id",
            "monitor",
            "monitor_name",
            "work_day",
            "actual_start",
            "actual_end",
            "normalized_start",
            "normalized_end",
            "scheduled_start",
            "scheduled_end",
            "normal_minutes",
            "overtime_minutes",
            "penalty_minutes",
            "late_minutes",
            "is_late",
            "lateness_excused",
            "lateness_exception",
            "lateness_exception_name",
            "session_state",
            "overtime_status",
            "overtime_auto_approved",
            "overtime_exception",
            "overtime_exception_name",
            "overtime_review_note",
        )


class OvertimeDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(required=False, allow_blank=True)
    penalize_on_reject = serializers.BooleanField(required=False, default=True)
