"""Rutas de contexto para el frontend de la plataforma central."""

from uuid import UUID

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import permissions
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.authentication import PlatformJWTAuthentication
from apps.users.api.serializers import UserSerializer


class PlatformMeAPIView(APIView):
    """Devuelve el perfil local asociado al JWT central que hizo la petición."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        claims = request.auth if isinstance(request.auth, dict) else {}
        return Response(
            {
                "usuario": UserSerializer(request.user).data,
                "plataforma": {
                    "usuarioExternoId": claims.get("sub"),
                    "nombreUsuario": claims.get("nombreUsuario"),
                    "roles": claims.get("roles", []),
                    "permisos": claims.get("permisos", []),
                },
            }
        )


class PlatformAdminIdentityAPIView(APIView):
    """Sincroniza la identidad local del administrador con un JWT central válido.

    Es una reparación explícita para instalaciones donde el UUID central cambió
    después de haber creado el usuario local ``admin``. No crea usuarios ni
    aplica la regla a otros nombres de usuario.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        header = request.headers.get("Authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise AuthenticationFailed("Se requiere un JWT central válido.")

        claims = PlatformJWTAuthentication()._decode_and_verify(token.strip())
        if claims.get("nombreUsuario") != "admin":
            raise AuthenticationFailed("Esta reparación está disponible únicamente para admin.")
        try:
            external_user_id = UUID(str(claims["sub"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationFailed("El token no contiene un sub UUID válido.") from exc

        User = get_user_model()
        with transaction.atomic():
            admin = User.objects.select_for_update().filter(
                username="admin", is_active=True, role="admin"
            ).first()
            if admin is None:
                raise AuthenticationFailed("No existe un administrador local activo llamado admin.")
            admin.usuario_externo_id = external_user_id
            admin.save(update_fields=["usuario_externo_id", "updated_at"])
        return Response({"vinculado": True})
