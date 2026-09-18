import pytest
from django.test import override_settings

from tests.factories import AdminUserFactory, UserFactory


@pytest.mark.django_db
def test_local_session_authenticates_a_monitores_profile(api_client):
    user = UserFactory()
    api_client.force_authenticate(user=user)

    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data["id"] == str(user.id)


@pytest.mark.django_db
def test_local_session_rejects_anonymous_user(api_client):
    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_local_admin_identity_can_access_the_monitores_session(api_client):
    admin = AdminUserFactory(username="admin")
    api_client.force_authenticate(user=admin)

    response = api_client.get("/api/v1/auth/me/")

    assert response.status_code == 200
    assert response.data["role"] == "admin"


@pytest.mark.django_db
def test_local_session_can_verify_its_own_password(api_client):
    user = UserFactory()
    user.set_password("ClaveSegura123456789")
    user.save()
    api_client.force_authenticate(user=user)

    accepted = api_client.post("/api/v1/auth/verify-password/", {"password": "ClaveSegura123456789"})
    rejected = api_client.post("/api/v1/auth/verify-password/", {"password": "incorrecta"})

    assert accepted.status_code == 200
    assert accepted.data == {"valido": True}
    assert rejected.status_code == 200
    assert rejected.data == {"valido": False}


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
