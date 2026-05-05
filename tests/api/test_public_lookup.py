import pytest

from apps.common.choices import DepartmentChoices, OvertimeStatusChoices
from tests.factories import MonitorFactory, WorkSessionFactory


@pytest.mark.django_db
def test_public_lookup_returns_limited_summary(api_client):
    monitor = MonitorFactory(codigo_estudiante="20231234", department=DepartmentChoices.PHYSICS)
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        schedule__monitor=monitor,
        normal_minutes=240,
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.APPROVED,
        penalty_minutes=0,
        late_minutes=6,
        is_late=True,
    )

    response = api_client.get(
        "/api/v1/reports/public-monitor-lookup/",
        {"codigo_estudiante": "20231234", "department": DepartmentChoices.PHYSICS},
    )

    assert response.status_code == 200
    assert response.data["monitor"]["codigo_estudiante"] == "20231234"
    assert response.data["metrics"]["approved_overtime_minutes"] == 60


@pytest.mark.django_db
def test_public_lookup_requires_correct_department(api_client):
    MonitorFactory(codigo_estudiante="20231234", department=DepartmentChoices.PHYSICS)

    response = api_client.get(
        "/api/v1/reports/public-monitor-lookup/",
        {"codigo_estudiante": "20231234", "department": DepartmentChoices.ELECTRICAL},
    )

    assert response.status_code == 404

