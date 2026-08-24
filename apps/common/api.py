"""Rutas de contexto para el frontend de la plataforma central."""

from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

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
