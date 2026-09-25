import hmac

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import permissions, serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.choices import DepartmentChoices, UserRoleChoices


class PlatformUserSyncSerializer(serializers.Serializer):
    external_user_id = serializers.UUIDField()
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=300)
    role = serializers.ChoiceField(choices=[UserRoleChoices.ADMIN, UserRoleChoices.LEADER], allow_null=True)
    department = serializers.ChoiceField(choices=DepartmentChoices.choices, allow_null=True, required=False)
    is_active = serializers.BooleanField()

    def validate(self, attrs):
        if attrs['role'] is None and attrs['is_active']:
            raise serializers.ValidationError({'role': 'Una cuenta activa debe tener un perfil de Monitores.'})
        if attrs['role'] == UserRoleChoices.LEADER and not attrs.get('department'):
            raise serializers.ValidationError({'department': 'Un líder debe tener una dependencia.'})
        if attrs['role'] == UserRoleChoices.ADMIN and attrs.get('department'):
            raise serializers.ValidationError({'department': 'Un administrador no debe tener dependencia.'})
        return attrs


class PlatformUserSyncAPIView(APIView):
    """Sincroniza identidades autorizadas desde Gestión de Aulas.

    La contraseña nunca viaja ni se duplica: estas cuentas solo entran con el
    JWT central y permanecen enlazadas por ``usuario_externo_id``.
    """

    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    # Solo el backend central, autenticado con el token de servicio, puede
    # usar esta ruta. No es una consulta pública y no debe agotarse al abrir
    # varias páginas de Monitores.
    throttle_classes = []

    def post(self, request):
        expected = settings.MONITORES_SERVICE_TOKEN
        supplied = request.headers.get('X-Monitores-Service-Token', '')
        if not expected or not hmac.compare_digest(supplied, expected):
            raise AuthenticationFailed('Token de integración inválido.')
        payload = PlatformUserSyncSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        User = get_user_model()
        user = User.objects.filter(usuario_externo_id=data['external_user_id']).first()
        if data['role'] is None:
            if user is not None:
                user.is_active = False
                user.save(update_fields=['is_active', 'updated_at'])
            return Response({'synchronized': True, 'active': False})
        # Una cuenta de Monitores creada antes de la integración puede tener
        # exactamente el mismo usuario y correo de la cuenta central. En ese
        # caso se enlaza para conservar sus registros y permitir el traspaso
        # de sesión. No se enlazan coincidencias parciales ni cuentas ya
        # asociadas a otra identidad central.
        if user is None:
            user = User.objects.filter(
                username__iexact=data['username'],
                email__iexact=data['email'],
                usuario_externo_id__isnull=True,
            ).first()

        conflicts = User.objects.filter(Q(username=data['username']) | Q(email=data['email']))
        if user is not None:
            conflicts = conflicts.exclude(pk=user.pk)
        if conflicts.exists():
            raise serializers.ValidationError('El usuario o correo ya pertenece a una cuenta local distinta.')
        if user is None:
            user = User(usuario_externo_id=data['external_user_id'])
        names = data['full_name'].strip().split(maxsplit=1)
        user.usuario_externo_id = data['external_user_id']
        user.username = data['username']
        user.email = data['email']
        user.first_name = names[0] if names else ''
        user.last_name = names[1] if len(names) > 1 else ''
        user.role = data['role']
        user.department = data.get('department') if data['role'] == UserRoleChoices.LEADER else None
        user.is_active = data['is_active']
        user.is_staff = data['role'] == UserRoleChoices.ADMIN
        user.is_superuser = data['role'] == UserRoleChoices.ADMIN
        user.set_unusable_password()
        user.full_clean()
        user.save()
        return Response({'id': str(user.id), 'synchronized': True})
