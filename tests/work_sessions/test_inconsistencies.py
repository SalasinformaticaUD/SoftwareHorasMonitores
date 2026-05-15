import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import AttendanceInconsistency, AttendanceInconsistencyEvent
from apps.common.choices import (
    AttendanceInconsistencyActionChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
)
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
