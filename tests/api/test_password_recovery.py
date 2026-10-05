import re
from urllib.parse import parse_qs, urlparse

import pytest
from django.core import mail

from apps.common.choices import DepartmentChoices, UserRoleChoices
from tests.factories import MonitorFactory, UserFactory


@pytest.fixture
def monitor_account():
    user = UserFactory(
        username="monitor.recuperacion@udistrital.edu.co",
        email="monitor.recuperacion@udistrital.edu.co",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
        password="ClaveAnterior123!",
    )
    monitor = MonitorFactory(user=user, codigo_estudiante="20261001001")
    return monitor, user


@pytest.mark.django_db
def test_password_recovery_sends_link_to_monitor_email(api_client, monitor_account, settings):
    settings.FRONTEND_BASE_URL = "http://frontend.test"

    response = api_client.post(
        "/api/v1/auth/password-recovery/request/",
        {"codigo_estudiante": monitor_account[0].codigo_estudiante},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["correo_destino"].startswith("mo***")
    assert response.data["correo_destino"].endswith("@udistrital.edu.co")
    assert response.data["correo_destino"] != monitor_account[1].email
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [monitor_account[1].email]
    assert "http://frontend.test/login?" in mail.outbox[0].body


@pytest.mark.django_db
def test_password_recovery_link_changes_password_and_is_single_use(api_client, monitor_account, settings):
    settings.FRONTEND_BASE_URL = "http://frontend.test"
    api_client.post(
        "/api/v1/auth/password-recovery/request/",
        {"codigo_estudiante": monitor_account[0].codigo_estudiante},
        format="json",
    )
    reset_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    query = parse_qs(urlparse(reset_url).query)
    payload = {
        "uid": query["reset_uid"][0],
        "token": query["reset_token"][0],
        "nueva_contrasena": "NuevaClaveSegura123!",
    }

    response = api_client.post("/api/v1/auth/password-recovery/confirm/", payload, format="json")
    repeated = api_client.post("/api/v1/auth/password-recovery/confirm/", payload, format="json")

    monitor_account[1].refresh_from_db()
    assert response.status_code == 200
    assert monitor_account[1].check_password("NuevaClaveSegura123!")
    assert repeated.status_code == 400


@pytest.mark.django_db
def test_password_recovery_does_not_reveal_unknown_student_code(api_client):
    response = api_client.post(
        "/api/v1/auth/password-recovery/request/",
        {"codigo_estudiante": "99999999999"},
        format="json",
    )

    assert response.status_code == 200
    assert "correo_destino" not in response.data
    assert len(mail.outbox) == 0


@pytest.mark.django_db
def test_historical_monitor_can_recover_password_and_log_in(api_client, monitor_account, settings):
    monitor, user = monitor_account
    monitor.is_active = False
    monitor.save(update_fields=["is_active", "updated_at"])
    monitor.semester.is_active = False
    monitor.semester.save(update_fields=["is_active", "updated_at"])
    settings.FRONTEND_BASE_URL = "http://frontend.test"

    request_response = api_client.post(
        "/api/v1/auth/password-recovery/request/",
        {"codigo_estudiante": monitor.codigo_estudiante},
        format="json",
    )
    reset_url = re.search(r"https?://\S+", mail.outbox[0].body).group(0)
    query = parse_qs(urlparse(reset_url).query)
    confirm_response = api_client.post(
        "/api/v1/auth/password-recovery/confirm/",
        {
            "uid": query["reset_uid"][0],
            "token": query["reset_token"][0],
            "nueva_contrasena": "ClaveHistoricaNueva123!",
        },
        format="json",
    )
    login_response = api_client.post(
        "/api/v1/auth/login/",
        {"username": monitor.codigo_estudiante, "password": "ClaveHistoricaNueva123!"},
        format="json",
    )

    assert request_response.status_code == 200
    assert confirm_response.status_code == 200
    assert login_response.status_code == 200
    assert login_response.data["id"] == str(user.id)


@pytest.mark.django_db
def test_monitor_without_configured_password_does_not_use_recovery(api_client, monitor_account):
    _monitor, user = monitor_account
    user.set_unusable_password()
    user.save(update_fields=["password", "updated_at"])

    response = api_client.post(
        "/api/v1/auth/password-recovery/request/",
        {"codigo_estudiante": monitor_account[0].codigo_estudiante},
        format="json",
    )

    assert response.status_code == 200
    assert "correo_destino" not in response.data
    assert len(mail.outbox) == 0
