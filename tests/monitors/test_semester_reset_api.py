from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.monitors.models import AcademicSemester, Monitor
from apps.monitors.platform_client import verify_platform_admin_password
from apps.schedules.models import Schedule
from tests.factories import AdminUserFactory, MonitorFactory, ScheduleFactory, UserFactory


pytestmark = pytest.mark.django_db
URL = "/api/v1/monitors/new-semester/"


def payload(password="ChangeMe123!"):
    return {
        "new_semester_name": "2026-3",
        "starts_on": "2026-08-01",
        "ends_on": "2026-12-15",
        "password": password,
        "confirm": True,
    }


def test_preview_is_admin_only_and_contains_all_historical_counts(api_client):
    monitor = MonitorFactory()
    ScheduleFactory(monitor=monitor)
    admin = AdminUserFactory()
    leader = UserFactory()

    api_client.force_authenticate(user=admin)
    preview = api_client.get(URL)
    assert preview.status_code == 200
    assert preview.data["preview"]["monitors"] == 1
    assert preview.data["preview"]["schedules"] == 1
    assert len(preview.data["preview"]) == 12

    api_client.force_authenticate(user=leader)
    assert api_client.get(URL).status_code == 403
    assert api_client.post(URL, payload(), format="json").status_code == 403


def test_wrong_or_missing_password_does_not_change_semester(api_client):
    monitor = MonitorFactory()
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)

    assert api_client.post(URL, payload("wrong"), format="json").status_code == 400
    missing = payload()
    missing.pop("password")
    assert api_client.post(URL, missing, format="json").status_code == 400
    monitor.refresh_from_db()
    assert monitor.is_active
    assert AcademicSemester.objects.get(name="2026-1").is_active
    assert not AcademicSemester.objects.filter(name="2026-3").exists()


def test_valid_password_archives_and_preserves_history(api_client):
    monitor = MonitorFactory()
    schedule = ScheduleFactory(monitor=monitor)
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)

    result = api_client.post(URL, payload(), format="json")

    assert result.status_code == 200, result.data
    assert result.data["new_semester"] == "2026-3"
    assert result.data["affected"]["monitors"] == 1
    monitor.refresh_from_db()
    schedule.refresh_from_db()
    assert not monitor.is_active
    assert not schedule.is_active
    assert Monitor.objects.filter(pk=monitor.pk).exists()
    assert Schedule.objects.filter(pk=schedule.pk).exists()
    assert AcademicSemester.objects.get(name="2026-1").archived_at is not None
    new_semester = AcademicSemester.objects.get(name="2026-3")
    assert new_semester.is_active
    assert new_semester.starts_on == date(2026, 8, 1)
    assert new_semester.ends_on == date(2026, 12, 15)


def test_duplicate_or_invalid_period_does_not_archive_current_semester(api_client):
    monitor = MonitorFactory()
    admin = AdminUserFactory()
    api_client.force_authenticate(user=admin)
    AcademicSemester.objects.create(name="2026-3", is_active=False)

    duplicate = api_client.post(URL, payload(), format="json")
    invalid = payload()
    invalid["new_semester_name"] = "2027-1"
    invalid["ends_on"] = "2026-07-01"
    invalid_response = api_client.post(URL, invalid, format="json")

    assert duplicate.status_code == 400
    assert invalid_response.status_code == 400
    monitor.refresh_from_db()
    assert monitor.is_active
    assert AcademicSemester.objects.get(name="2026-1").is_active
    assert not AcademicSemester.objects.filter(name="2027-1").exists()


@patch("apps.monitors.api.views.verify_platform_admin_password")
def test_central_admin_password_is_verified_before_archiving(verify_password, api_client):
    monitor = MonitorFactory()
    admin = AdminUserFactory(usuario_externo_id=uuid4())
    admin.set_unusable_password()
    admin.save(update_fields=["password"])
    api_client.force_authenticate(user=admin)

    verify_password.return_value = False
    assert api_client.post(URL, payload(), format="json").status_code == 400
    monitor.refresh_from_db()
    assert monitor.is_active

    verify_password.side_effect = ValidationError("Gestión de Aulas no disponible.")
    assert api_client.post(URL, payload(), format="json").status_code == 400
    monitor.refresh_from_db()
    assert monitor.is_active

    verify_password.side_effect = None
    verify_password.return_value = True
    assert api_client.post(URL, payload(), format="json").status_code == 200
    verify_password.assert_called_with(authorization="", password="ChangeMe123!")


@override_settings(PLATFORM_API_URL="http://aulas.example.test", PLATFORM_API_TIMEOUT_SECONDS=3)
@patch("apps.monitors.platform_client.urlopen")
def test_platform_password_verification_uses_central_endpoint(urlopen):
    urlopen.return_value.__enter__.return_value.read.return_value = b'{"valido": true}'

    assert verify_platform_admin_password(
        authorization="Bearer token-central", password="ClaveSegura123!"
    )

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://aulas.example.test/auth/verificar-contrasena"
    assert request.get_header("Authorization") == "Bearer token-central"
    assert b'"password": "ClaveSegura123!"' in request.data
