from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from apps.common.choices import DepartmentChoices, UserRoleChoices

User = get_user_model()
ADMINISTRABLE_ROLES = [UserRoleChoices.ADMIN, UserRoleChoices.LEADER]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate
        from apps.monitors.models import Monitor

        identifier = attrs["username"].strip()
        monitor = (
            Monitor.objects.select_related("user")
            .filter(
                codigo_estudiante__iexact=identifier,
                user__is_active=True,
            )
            .order_by("-is_active", "-semester__is_active", "-created_at")
            .first()
        )
        if monitor is not None:
            login_username = monitor.user.username
        else:
            administrative_user = (
                User.objects.filter(
                    username__iexact=identifier,
                    role__in=[UserRoleChoices.ADMIN, UserRoleChoices.LEADER],
                    is_active=True,
                )
                .only("username")
                .first()
            )
            login_username = administrative_user.username if administrative_user else None

        user = None
        if login_username:
            user = authenticate(
                request=self.context.get("request"),
                username=login_username,
                password=attrs["password"],
            )
        if not user or not user.is_active:
            raise serializers.ValidationError("Credenciales inválidas.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    monitor_is_current = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "usuario_externo_id", "username", "email", "first_name", "last_name", "role", "department", "monitor_is_current")

    def get_monitor_is_current(self, obj):
        if obj.role != UserRoleChoices.MONITOR:
            return None
        return obj.monitor_profiles.filter(is_active=True, semester__is_active=True).exists()


class ManagedUserSerializer(UserSerializer):
    full_name = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ("full_name", "source", "is_active", "is_staff", "created_at", "updated_at")
        read_only_fields = fields

    def get_full_name(self, obj):
        return obj.display_name

    def get_source(self, obj):
        return "AULAS" if obj.usuario_externo_id else "MONITORES"


class ManagedUserWriteSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    role = serializers.ChoiceField(choices=[UserRoleChoices.ADMIN, UserRoleChoices.LEADER])
    department = serializers.ChoiceField(choices=DepartmentChoices.choices, required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)

    def validate_username(self, value):
        instance = self.instance
        query = User.objects.filter(username__iexact=value)
        if instance:
            query = query.exclude(pk=instance.pk)
        if query.exists():
            raise serializers.ValidationError("Este nombre de usuario ya está en uso.")
        return value.strip()

    def validate_email(self, value):
        instance = self.instance
        query = User.objects.filter(email__iexact=value)
        if instance:
            query = query.exclude(pk=instance.pk)
        if query.exists():
            raise serializers.ValidationError("Este correo ya está en uso.")
        return value.strip().lower()

    def validate(self, attrs):
        role = attrs.get("role", getattr(self.instance, "role", None))
        department = attrs.get("department", getattr(self.instance, "department", None))
        if role == UserRoleChoices.LEADER and not department:
            raise serializers.ValidationError({"department": "Un líder debe tener una dependencia."})
        if role == UserRoleChoices.ADMIN and department:
            raise serializers.ValidationError({"department": "Un administrador no debe tener dependencia."})
        return attrs


class ManagedUserCreateSerializer(ManagedUserWriteSerializer):
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)


class MonitorPasswordRecoveryRequestSerializer(serializers.Serializer):
    codigo_estudiante = serializers.RegexField(r"^\d+$", max_length=20)


class MonitorPasswordRecoveryConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(write_only=True)
    token = serializers.CharField(write_only=True)
    nueva_contrasena = serializers.CharField(write_only=True, min_length=10, max_length=128, trim_whitespace=False)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True, role=UserRoleChoices.MONITOR)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"token": "El enlace de recuperación no es válido o ya venció."})
        if user.usuario_externo_id or not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "El enlace de recuperación no es válido o ya venció."})
        try:
            validate_password(attrs["nueva_contrasena"], user=user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"nueva_contrasena": list(exc.messages)}) from exc
        attrs["user"] = user
        return attrs
