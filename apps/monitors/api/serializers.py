from rest_framework import serializers

from apps.monitors.models import Monitor


class MonitorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Monitor
        fields = ("id", "codigo_estudiante", "full_name", "department", "is_active")

