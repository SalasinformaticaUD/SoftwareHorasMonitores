import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceInconsistency, AttendanceInconsistencyEvent
from apps.common.choices import (
    AttendanceInconsistencyActionChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
    DepartmentChoices,
)
from apps.monitors.models import AcademicSemester
from tests.factories import AttendanceRawRecordFactory, MonitorFactory, UserFactory


@pytest.mark.django_db
def test_inconsistency_history_excludes_detected_and_duplicate_auto_resolved_events():
    user = UserFactory()
    monitor = MonitorFactory(full_name="Ana Torres")
    raw_record = AttendanceRawRecordFactory(monitor=monitor)
    inconsistency = AttendanceInconsistency.objects.create(
        raw_record=raw_record,
        monitor=monitor,
        work_day=raw_record.work_day,
        inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
        status=AttendanceInconsistencyStatusChoices.RESOLVED,
        detected_at=timezone.now(),
        message="Duplicado detectado",
        resolution_note="Invalidada automaticamente por duplicidad.",
    )
    AttendanceInconsistencyEvent.objects.create(
        inconsistency=inconsistency,
        action=AttendanceInconsistencyActionChoices.DETECTED,
        note="Detectada como duplicado.",
    )
    AttendanceInconsistencyEvent.objects.create(
        inconsistency=inconsistency,
        action=AttendanceInconsistencyActionChoices.AUTO_RESOLVED,
        note="Marcacion duplicada invalidada automaticamente.",
    )

    client = Client()
    client.force_login(user)
    response = client.get(reverse("inconsistencies-manage"))

    assert response.status_code == 200
    assert response.context["resolved_duplicate_inconsistencies"].count() == 1
    assert response.context["recent_inconsistency_events"].count() == 0
    content = response.content.decode("utf-8")
    assert "Detectada como duplicado." not in content
    assert "Marcacion duplicada invalidada automaticamente." not in content


@pytest.mark.django_db
def test_inconsistency_view_only_shows_current_semester_records(client):
    AcademicSemester.objects.update(is_active=False)
    old_semester, _created = AcademicSemester.objects.get_or_create(name="2026-1")
    old_semester.is_active = False
    old_semester.save(update_fields=["is_active", "updated_at"])
    current_semester = AcademicSemester.objects.create(name="2026-3", is_active=True)
    leader = UserFactory(department=DepartmentChoices.ELECTRICAL)
    old_monitor = MonitorFactory(
        full_name="Monitor Semestre Anterior",
        department=DepartmentChoices.ELECTRICAL,
        semester=old_semester,
        is_active=False,
    )
    current_monitor = MonitorFactory(
        full_name="Monitor Semestre Actual",
        department=DepartmentChoices.ELECTRICAL,
        semester=current_semester,
    )
    old_raw_record = AttendanceRawRecordFactory(monitor=old_monitor, raw_full_name=old_monitor.full_name)
    current_raw_record = AttendanceRawRecordFactory(monitor=current_monitor, raw_full_name=current_monitor.full_name)
    AttendanceInconsistency.objects.create(
        raw_record=old_raw_record,
        monitor=old_monitor,
        work_day=old_raw_record.work_day,
        inconsistency_type=AttendanceInconsistencyTypeChoices.END_OF_DAY,
        status=AttendanceInconsistencyStatusChoices.PENDING,
        detected_at=timezone.now(),
        message="Inconsistencia del semestre anterior",
    )
    AttendanceInconsistency.objects.create(
        raw_record=current_raw_record,
        monitor=current_monitor,
        work_day=current_raw_record.work_day,
        inconsistency_type=AttendanceInconsistencyTypeChoices.END_OF_DAY,
        status=AttendanceInconsistencyStatusChoices.PENDING,
        detected_at=timezone.now(),
        message="Inconsistencia del semestre actual",
    )

    client.force_login(leader)
    response = client.get(reverse("inconsistencies-manage"))

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    assert "Monitor Semestre Actual" in content
    assert "Inconsistencia del semestre actual" in content
    assert "Monitor Semestre Anterior" not in content
    assert "Inconsistencia del semestre anterior" not in content
    assert response.context["stats"]["attendance_inconsistencies"] == 1
