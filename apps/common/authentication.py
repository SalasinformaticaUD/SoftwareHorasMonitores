"""Autenticación de la API mediante los JWT emitidos por la plataforma central."""

import base64
import binascii
import hashlib
import hmac
import json
import time
from uuid import UUID

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import exceptions
from rest_framework.authentication import BaseAuthentication


class PlatformJWTAuthentication(BaseAuthentication):
    """Valida tokens HS256 de Gestión de Aulas sin compartir su base de datos."""

    keyword = "Bearer"

    def authenticate(self, request):
        header = request.headers.get("Authorization", "")
        if not header:
            return None

        scheme, _, token = header.partition(" ")
        if scheme.lower() != self.keyword.lower() or not token or " " in token.strip():
            raise exceptions.AuthenticationFailed("Authorization debe usar Bearer JWT.")

        payload = self._decode_and_verify(token.strip())
        try:
            external_user_id = UUID(payload["sub"])
        except (KeyError, TypeError, ValueError):
            raise exceptions.AuthenticationFailed("El token no contiene un sub UUID válido.")

        user = get_user_model().objects.filter(usuario_externo_id=external_user_id, is_active=True).first()
        if user is None:
            raise exceptions.AuthenticationFailed("El usuario de plataforma no está vinculado en Monitores.")
        return user, payload

    def authenticate_header(self, _request):
        return self.keyword

    def _decode_and_verify(self, token):
        secret = settings.PLATFORM_JWT_SECRET.encode("utf-8")
        if not secret:
            raise exceptions.AuthenticationFailed("La integración JWT no está configurada.")

        parts = token.split(".")
        if len(parts) != 3:
            raise exceptions.AuthenticationFailed("JWT inválido.")
        encoded_header, encoded_payload, encoded_signature = parts
        try:
            header = self._decode_json(encoded_header)
            payload = self._decode_json(encoded_payload)
            signature = self._decode_base64url(encoded_signature)
        except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
            raise exceptions.AuthenticationFailed("JWT inválido.")

        if header.get("alg") != "HS256":
            raise exceptions.AuthenticationFailed("El algoritmo JWT no está permitido.")
        expected_signature = hmac.new(
            secret,
            f"{encoded_header}.{encoded_payload}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        if not hmac.compare_digest(signature, expected_signature):
            raise exceptions.AuthenticationFailed("Firma JWT inválida.")

        expires_at = payload.get("exp")
        if not isinstance(expires_at, (int, float)) or expires_at <= time.time():
            raise exceptions.AuthenticationFailed("Token vencido o sin expiración válida.")
        return payload

    @staticmethod
    def _decode_base64url(value):
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

    @classmethod
    def _decode_json(cls, value):
        return json.loads(cls._decode_base64url(value).decode("utf-8"))
