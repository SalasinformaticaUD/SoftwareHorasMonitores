from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.api.serializers import LoginSerializer, UserSerializer


class LoginAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        login(request, serializer.validated_data["user"])
        return Response(UserSerializer(serializer.validated_data["user"]).data)


class LogoutAPIView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class VerifyPasswordAPIView(APIView):
    """Confirma la clave de la sesión local antes de una acción sensible."""

    def post(self, request):
        password = request.data.get("password")
        if not isinstance(password, str) or not password:
            return Response(
                {"password": ["La contraseña es obligatoria."]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"valido": request.user.check_password(password)})


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeAPIView(APIView):
    def get(self, request):
        return Response(UserSerializer(request.user).data)

