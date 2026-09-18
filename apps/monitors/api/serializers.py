from rest_framework import serializers

from apps.common.choices import DepartmentChoices
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
            "numero_documento",
            "proyecto_curricular",
            "telefono",
            "is_active",
        )


class PlatformMonitorProvisionSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    codigo_estudiante = serializers.RegexField(r"^\d+$", max_length=20)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=80, required=False, allow_blank=False)
    department = serializers.ChoiceField(choices=DepartmentChoices.choices)
    numero_documento = serializers.RegexField(r"^\d+$", max_length=32)
    proyecto_curricular = serializers.CharField(max_length=64)
    telefono = serializers.RegexField(r"^\d+$", max_length=32)
    confirm_repeating_monitor = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        attrs["username"] = attrs.get("username", attrs["email"].split("@", 1)[0]).strip()
        for field in ("full_name", "codigo_estudiante", "numero_documento", "proyecto_curricular", "telefono"):
            if not attrs[field].strip():
                raise serializers.ValidationError({field: "Este campo es obligatorio."})
        return attrs
