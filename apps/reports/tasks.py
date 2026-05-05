from datetime import date
from typing import Optional

from celery import shared_task

from apps.monitors.models import Monitor
from apps.reports.services import generate_monitor_report


@shared_task
def generate_monitor_report_task(
    monitor_id: str,
    start_date: str,
    end_date: str,
    generated_by_id: Optional[str] = None,
):
    monitor = Monitor.objects.get(pk=monitor_id)
    generated_by = None
    if generated_by_id:
        from apps.users.models import User

        generated_by = User.objects.get(pk=generated_by_id)
    snapshot = generate_monitor_report(
        monitor=monitor,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
        generated_by=generated_by,
    )
    return str(snapshot.id)
