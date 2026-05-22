from datetime import date
from types import SimpleNamespace

import pytest
from django.test import RequestFactory
from django.template.loader import render_to_string

from apps.common.choices import OvertimeStatusChoices
from tests.factories import UserFactory, WorkSessionFactory


@pytest.mark.django_db
def test_overtime_review_links_to_monitor_day_records():
    session = WorkSessionFactory(
        raw_record__work_day=date(2026, 4, 30),
        work_day=date(2026, 4, 30),
        overtime_minutes=60,
        overtime_status=OvertimeStatusChoices.PENDING,
    )
    request = RequestFactory().get("/overtime/review/")
    request.user = UserFactory()
    request.resolver_match = SimpleNamespace(url_name="overtime-review")

    html = render_to_string(
        "work_sessions/overtime_review.html",
        {"sessions": [session]},
        request=request,
    )

    assert "Ver registro" in html
    assert f"/dashboard/monitor/{session.monitor.id}/registros/?dia=2026-04-30#record-day-2026-04-30" in html
