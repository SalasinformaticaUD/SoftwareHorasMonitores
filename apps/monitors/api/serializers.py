from rest_framework import serializers

from apps.monitors.models import Monitor


class MonitorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    usuario_externo_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Monitor
        fields = (
            "id",
            "usuario_externo_id",
            "user_email",
            "codigo_estudiante",
            "full_name",
            "department",
            "is_active",
        )
