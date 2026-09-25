from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.choices import DepartmentChoices, UserRoleChoices

User = get_user_model()
ADMINISTRABLE_ROLES = [UserRoleChoices.ADMIN, UserRoleChoices.LEADER]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        from django.contrib.auth import authenticate

        user = authenticate(
            request=self.context.get("request"),
            username=attrs["username"],
            password=attrs["password"],
        )
        if not user or not user.is_active:
            raise serializers.ValidationError("Credenciales inválidas.")
        attrs["user"] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "usuario_externo_id", "username", "email", "first_name", "last_name", "role", "department")


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