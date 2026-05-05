from datetime import date
from typing import Optional

from django.db.models import Q

from apps.common.choices import UserRoleChoices
from apps.common.utils import overlap_in_minutes
from apps.schedules.models import Schedule, ScheduleException


def schedule_for_monitor_and_day(monitor, day: date, start_time=None, end_time=None) -> Optional[Schedule]:
    schedules = list(
        Schedule.objects.filter(
            monitor=monitor,
            weekday=day.weekday(),
            is_active=True,
        ).order_by("start_time")
    )
    if not schedules:
        return None
    if start_time is None or end_time is None:
        return schedules[0]

    best_schedule = None
    best_overlap = 0
    for schedule in schedules:
        overlap = overlap_in_minutes(start_time, end_time, schedule.start_time, schedule.end_time)
        if overlap > best_overlap:
            best_schedule = schedule
            best_overlap = overlap
    return best_schedule if best_overlap > 0 else None


def _active_exception_queryset(*, monitor, day: date):
    base_queryset = ScheduleException.objects.filter(
        is_active=True,
        start_date__lte=day,
        end_date__gte=day,
    )
    department_specific = base_queryset.filter(department=monitor.department).order_by("-start_date", "name")
    if department_specific.exists():
        return department_specific
    return base_queryset.filter(Q(department__isnull=True) | Q(department="")).order_by("-start_date", "name")


def lateness_exception_for(*, monitor, day: date) -> Optional[ScheduleException]:
    return _active_exception_queryset(monitor=monitor, day=day).filter(ignore_lateness=True).first()


def overtime_exception_for(*, monitor, day: date) -> Optional[ScheduleException]:
    return _active_exception_queryset(monitor=monitor, day=day).filter(approve_overtime=True).first()


def visible_schedule_exceptions_for_user(user):
    queryset = ScheduleException.objects.order_by("-start_date", "name")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(Q(department=user.department) | Q(department__isnull=True) | Q(department=""))
