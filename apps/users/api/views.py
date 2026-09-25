from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import LOCAL_MONITORES_TOKEN_MAX_AGE_SECONDS, issue_local_monitor_token
from apps.common.choices import UserRoleChoices
from apps.users.api.serializers import (
    LoginSerializer,
    ManagedUserCreateSerializer,
    ManagedUserSerializer,
    ManagedUserWriteSerializer,
    PasswordResetSerializer,
    UserSerializer,
)

User = get_user_model()


class IsMonitoresAdmin(permissions.BasePermission):
    message = "Solo el administrador de Gestión de Monitores puede administrar usuarios."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == UserRoleChoices.ADMIN
        )


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        payload = UserSerializer(user).data
        payload.update({
            "access_token": issue_local_monitor_token(user),
            "expires_in": LOCAL_MONITORES_TOKEN_MAX_AGE_SECONDS,
        })
        return Response(payload)


class LogoutAPIView(APIView):
    def post(self, request):
        from django.contrib.auth import logout

        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyPasswordAPIView(APIView):
    """Confirma la clave de la sesión local antes de una acción sensible."""

    def post(self, request):
        password = request.data.get("password")
        if not isinstance(password, str) or not password:
            return Response({"password": ["La contraseña es obligatoria."]}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"valido": request.user.check_password(password)})


class MeAPIView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ManagedUserListCreateAPIView(APIView):
    permission_classes = [IsMonitoresAdmin]

    def get(self, request):
        users = User.objects.filter(role__in=[UserRoleChoices.ADMIN, UserRoleChoices.LEADER]).order_by("role", "first_name", "last_name", "username")
        return Response(ManagedUserSerializer(users, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = ManagedUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = User.objects.create_user(
            username=data["username"],
            email=data["email"],
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            role=data["role"],
            department=data.get("department") if data["role"] == UserRoleChoices.LEADER else None,
            is_active=data.get("is_active", True),
            is_staff=data["role"] == UserRoleChoices.ADMIN,
        )
        return Response(ManagedUserSerializer(user).data, status=status.HTTP_201_CREATED)


class ManagedUserDetailAPIView(APIView):
    permission_classes = [IsMonitoresAdmin]

    def get_object(self, user_id):
        try:
            return User.objects.get(pk=user_id, role__in=[UserRoleChoices.ADMIN, UserRoleChoices.LEADER])
        except User.DoesNotExist as exc:
            raise PermissionDenied("El usuario administrativo no existe.") from exc

    def patch(self, request, user_id):
        user = self.get_object(user_id)
        self.exigir_cuenta_local(user)
        serializer = ManagedUserWriteSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        for field in ("username", "email", "first_name", "last_name", "role", "is_active"):
            if field in data:
                setattr(user, field, data[field])
        if "role" in data or "department" in data:
            user.department = data.get("department") if user.role == UserRoleChoices.LEADER else None
        user.is_staff = user.role == UserRoleChoices.ADMIN
        user.save()
        return Response(ManagedUserSerializer(user).data)

    def exigir_cuenta_local(self, user):
        if user.usuario_externo_id:
            raise PermissionDenied("Esta cuenta proviene de Gestión de Aulas. Modifica su cargo o sus datos desde Aulas.")


class ManagedUserPasswordAPIView(ManagedUserDetailAPIView):
    def post(self, request, user_id):
        user = self.get_object(user_id)
        self.exigir_cuenta_local(user)
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data["password"])
        user.save(update_fields=["password", "updated_at"])
        return Response({"updated": True})