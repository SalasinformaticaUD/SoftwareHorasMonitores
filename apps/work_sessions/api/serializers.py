from rest_framework import serializers

from apps.work_sessions.models import WorkSession


class WorkSessionSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)
    lateness_exception_name = serializers.CharField(source="lateness_exception.name", read_only=True)
    overtime_exception_name = serializers.CharField(source="overtime_exception.name", read_only=True)
    overtime_reviewed_by_name = serializers.SerializerMethodField()
    overtime_rejection_penalized = serializers.SerializerMethodField()

    def get_overtime_reviewed_by_name(self, obj):
        reviewer = obj.overtime_reviewed_by
        if reviewer is None:
            return ""
        return reviewer.get_full_name().strip() or reviewer.username

    def get_overtime_rejection_penalized(self, obj):
        if obj.overtime_status != "rejected":
            return False
        return obj.annotations.filter(action="deduct", delta_minutes=-obj.overtime_minutes).exists()

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
            "overtime_reviewed_by_name",
            "overtime_reviewed_at",
            "overtime_rejection_penalized",
            "invalidated_by",
            "invalidated_at",
            "invalidation_reason",
        )


class OvertimeDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(required=False, allow_blank=True)
    penalize_on_reject = serializers.BooleanField(required=False, default=True)
