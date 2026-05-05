from rest_framework import serializers

from apps.schedules.models import Schedule, ScheduleException


class ScheduleSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)

    class Meta:
        model = Schedule
        fields = (
            "id",
            "monitor",
            "monitor_name",
            "weekday",
            "start_time",
            "end_time",
            "is_active",
        )


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    department_label = serializers.CharField(source="get_department_display", read_only=True)

    class Meta:
        model = ScheduleException
        fields = (
            "id",
            "name",
            "description",
            "start_date",
            "end_date",
            "department",
            "department_label",
            "ignore_lateness",
            "approve_overtime",
            "is_active",
        )
