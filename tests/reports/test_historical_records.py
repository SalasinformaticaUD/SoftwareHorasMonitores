import pytest
from django.urls import reverse

from apps.common.choices import DepartmentChoices
from apps.monitors.models import AcademicSemester
from tests.factories import AdminUserFactory, MonitorFactory, UserFactory, WorkSessionFactory


pytestmark = pytest.mark.django_db


def archived_semester(name="2026-1"):
    semester, _created = AcademicSemester.objects.get_or_create(name=name)
    semester.is_active = False
    semester.save(update_fields=["is_active", "updated_at"])
    return semester


def test_admin_historical_records_are_split_by_department_and_semester(client):
    admin = AdminUserFactory()
    semester = archived_semester()
    physics_monitor = MonitorFactory(
        full_name="Historico Fisica",
        department=DepartmentChoices.PHYSICS,
        semester=semester,
        is_active=False,
    )
    labs_monitor = MonitorFactory(
        full_name="Historico Labs",
        department=DepartmentChoices.INFORMATICS_LABS,
        semester=semester,
        is_active=False,
    )
    client.force_login(admin)

    response = client.get(reverse("historical-records"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Monitores Fisica" in content
    assert "Monitores Aulas de Software" in content
    assert "Historico Fisica" not in content
    assert "Historico Labs" not in content

    response = client.get(
        reverse("historical-records"),
        {"department": DepartmentChoices.PHYSICS, "semester": str(semester.id)},
    )
    content = response.content.decode()

    assert physics_monitor.full_name in content
    assert labs_monitor.full_name not in content
    assert reverse(
        "historical-department-semester-export",
        args=[DepartmentChoices.PHYSICS, semester.id],
    ) in content


def test_leader_historical_records_only_show_own_department(client):
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    semester = archived_semester()
    visible_monitor = MonitorFactory(
        full_name="Historico Electrica",
        department=DepartmentChoices.ELECTRICAL,
        semester=semester,
        is_active=False,
    )
    hidden_monitor = MonitorFactory(
        full_name="Historico Fisica",
        department=DepartmentChoices.PHYSICS,
        semester=semester,
        is_active=False,
    )
    client.force_login(leader)

    response = client.get(
        reverse("historical-records"),
        {"department": DepartmentChoices.PHYSICS, "semester": str(semester.id)},
    )
    content = response.content.decode()

    assert "Monitores Laboratorios" in content
    assert "Monitores Fisica" not in content
    assert visible_monitor.full_name in content
    assert hidden_monitor.full_name not in content


def test_historical_export_downloads_department_semester_excel(client):
    admin = AdminUserFactory()
    semester = archived_semester()
    monitor = MonitorFactory(
        full_name="Historico Export",
        department=DepartmentChoices.PHYSICS,
        semester=semester,
        is_active=False,
    )
    WorkSessionFactory(monitor=monitor, schedule__monitor=monitor, normal_minutes=120)
    client.force_login(admin)

    response = client.get(
        reverse(
            "historical-department-semester-export",
            args=[DepartmentChoices.PHYSICS, semester.id],
        )
    )

    assert response.status_code == 200
    assert response["Content-Type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "historico_physics_2026-1.xlsx" in response["Content-Disposition"]
