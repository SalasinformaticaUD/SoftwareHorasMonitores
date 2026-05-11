from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

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
            "location",
            "is_active",
        )

    def validate(self, attrs):
        data = {
            "monitor": attrs.get("monitor", getattr(self.instance, "monitor", None)),
            "weekday": attrs.get("weekday", getattr(self.instance, "weekday", None)),
            "start_time": attrs.get("start_time", getattr(self.instance, "start_time", None)),
            "end_time": attrs.get("end_time", getattr(self.instance, "end_time", None)),
            "location": attrs.get("location", getattr(self.instance, "location", "")),
            "is_active": attrs.get("is_active", getattr(self.instance, "is_active", True)),
        }
        schedule = Schedule(**data)
        if self.instance:
            schedule.pk = self.instance.pk
        try:
            schedule.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


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
