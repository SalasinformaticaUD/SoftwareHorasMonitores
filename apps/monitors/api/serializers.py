from rest_framework import serializers

from apps.common.choices import DepartmentChoices
from apps.monitors.models import Monitor


class MonitorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    usuario_externo_id = serializers.UUIDField(read_only=True)
    semester = serializers.CharField(source="semester.name", read_only=True, allow_null=True)
    semester_is_active = serializers.BooleanField(source="semester.is_active", read_only=True, allow_null=True)
    account_status = serializers.SerializerMethodField()
    activation_email_sent = serializers.SerializerMethodField()
    has_previous_monitoring = serializers.SerializerMethodField()

    def get_account_status(self, obj):
        if not obj.is_active:
            return "INACTIVE"
        if not obj.user or not obj.user.has_usable_password():
            return "PENDING"
        return "ACTIVE"

    def get_activation_email_sent(self, obj):
        return bool(getattr(obj, "_activation_email_sent", False))

    def get_has_previous_monitoring(self, obj):
        history = Monitor.objects.exclude(pk=obj.pk).filter(semester__is_active=False)
        if obj.user_id:
            history = history.filter(user_id=obj.user_id)
        else:
            history = history.filter(codigo_estudiante=obj.codigo_estudiante)
        return history.exists()

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
            "semester",
            "semester_is_active",
            "account_status",
            "activation_email_sent",
            "has_previous_monitoring",
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


class SemesterResetSerializer(serializers.Serializer):
    new_semester_name = serializers.CharField(max_length=20)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    confirm = serializers.BooleanField()

    def validate(self, attrs):
        if not attrs["confirm"]:
            raise serializers.ValidationError({"confirm": "Debes confirmar el inicio del nuevo semestre."})
        if attrs["ends_on"] < attrs["starts_on"]:
            raise serializers.ValidationError({"ends_on": "La fecha final no puede ser anterior a la fecha inicial."})
        return attrs
