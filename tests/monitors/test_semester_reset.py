import pytest
from django.urls import reverse

from apps.annotations.models import Annotation
from apps.attendance.models import AttendanceImportJob
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor
from apps.reports.models import MonitorMemorandum
from apps.schedules.models import ScheduleException
from apps.work_sessions.models import WorkSession
from django.contrib.auth import get_user_model
from tests.factories import (
    AdminUserFactory,
    AnnotationFactory,
    AttendanceRawRecordFactory,
    MonitorFactory,
    ScheduleExceptionFactory,
    UserFactory,
    WorkSessionFactory,
)


pytestmark = pytest.mark.django_db
User = get_user_model()


def test_semester_reset_button_is_visible_only_for_admin(client):
    admin = AdminUserFactory()
    leader = UserFactory(department=DepartmentChoices.PHYSICS)

    client.force_login(admin)
    admin_response = client.get(reverse("admin-monitors"))
    assert "Iniciar semestre nuevo" in admin_response.content.decode()

    client.force_login(leader)
    leader_response = client.get(reverse("admin-monitors"))
    assert "Iniciar semestre nuevo" not in leader_response.content.decode()


def test_leader_cannot_open_semester_reset(client):
    leader = UserFactory(department=DepartmentChoices.PHYSICS)
    client.force_login(leader)

    response = client.get(reverse("admin-semester-reset"))

    assert response.status_code == 403


def test_semester_reset_rejects_wrong_password_and_keeps_data(client):
    admin = AdminUserFactory()
    monitor = MonitorFactory()
    client.force_login(admin)

    response = client.post(reverse("admin-semester-reset"), {"password": "wrong-password"})

    assert response.status_code == 200
    assert "La contrasena no coincide" in response.content.decode()
    assert Monitor.objects.filter(pk=monitor.pk).exists()


def test_semester_reset_archives_operational_data_and_preserves_monitor_accounts(client):
    admin = AdminUserFactory(username="admin-reset")
    leader = UserFactory(username="leader-reset", department=DepartmentChoices.PHYSICS)
    monitor_user = UserFactory(
        username="monitor-reset",
        email="monitor-reset@example.edu",
        role=UserRoleChoices.MONITOR,
        department=DepartmentChoices.PHYSICS,
        is_staff=False,
    )
    monitor = MonitorFactory(user=monitor_user, department=DepartmentChoices.PHYSICS)
    raw_record = AttendanceRawRecordFactory(monitor=monitor)
    WorkSessionFactory(raw_record=raw_record, monitor=monitor, schedule__monitor=monitor)
    AnnotationFactory(monitor=monitor, leader=leader)
    ScheduleExceptionFactory(department=DepartmentChoices.PHYSICS)
    MonitorMemorandum.objects.create(monitor=monitor, late_count_threshold=3, sent_to=monitor_user.email)

    client.force_login(admin)
    response = client.post(
        reverse("admin-semester-reset"),
        {"new_semester_name": "2026-3", "password": "ChangeMe123!"},
    )

    assert response.status_code == 302
    assert response.url == reverse("admin-monitors")
    monitor.refresh_from_db()
    assert monitor.is_active is False
    assert Monitor.objects.count() == 1
    assert User.objects.filter(role=UserRoleChoices.MONITOR).count() == 1
    assert User.objects.filter(pk=monitor_user.pk, is_active=True).exists()
    assert User.objects.filter(pk=admin.pk).exists()
    assert User.objects.filter(pk=leader.pk).exists()
    assert WorkSession.objects.count() == 1
    assert AttendanceImportJob.objects.count() == 1
    assert Annotation.objects.count() == 1
    assert MonitorMemorandum.objects.count() == 1
    assert ScheduleException.objects.count() == 1
    assert AcademicSemester.objects.get(name="2026-1").is_active is False
    assert AcademicSemester.objects.get(name="2026-3").is_active is True
