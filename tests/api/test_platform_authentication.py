import base64
import hashlib
import hmac
import json
import time
import uuid

import pytest
from django.test import override_settings

from tests.factories import UserFactory


def _token(*, secret, subject, expires_in=300):
    def encode(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()

    header = encode({"alg": "HS256", "typ": "JWT"})
    payload = encode(
        {
            "sub": str(subject),
            "nombreUsuario": "leader.physics",
            "roles": ["LIDER"],
            "permisos": ["MONITORES_LEER"],
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
        }
    )
    signature = hmac.new(secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


@pytest.mark.django_db
@override_settings(PLATFORM_JWT_SECRET="platform-test-secret")
def test_platform_jwt_authenticates_a_linked_local_profile(api_client):
    external_user_id = uuid.uuid4()
    user = UserFactory(usuario_externo_id=external_user_id)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {_token(secret='platform-test-secret', subject=external_user_id)}")

    response = api_client.get("/api/v1/platform/me/")

    assert response.status_code == 200
    assert response.data["usuario"]["id"] == str(user.id)
    assert response.data["plataforma"]["usuarioExternoId"] == str(external_user_id)


@pytest.mark.django_db
@override_settings(PLATFORM_JWT_SECRET="platform-test-secret")
def test_platform_jwt_rejects_an_unlinked_user(api_client):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {_token(secret='platform-test-secret', subject=uuid.uuid4())}"
    )

    response = api_client.get("/api/v1/platform/me/")

    assert response.status_code == 401


@pytest.mark.django_db
@override_settings(CORS_ALLOWED_ORIGINS=["http://frontend.test"])
def test_api_allows_cors_preflight_only_for_the_general_frontend(client):
    response = client.options(
        "/api/v1/platform/me/",
        HTTP_ORIGIN="http://frontend.test",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
    )

    assert response.status_code == 204
    assert response["Access-Control-Allow-Origin"] == "http://frontend.test"
