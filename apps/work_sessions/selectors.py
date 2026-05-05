from django.db.models import QuerySet, Sum

from apps.common.choices import OvertimeStatusChoices, UserRoleChoices
from apps.work_sessions.models import WorkSession


def visible_sessions_for_user(user) -> QuerySet[WorkSession]:
    queryset = WorkSession.objects.select_related("monitor", "schedule", "raw_record")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(monitor__department=user.department)


def pending_overtime_sessions_for_user(user) -> QuerySet[WorkSession]:
    return visible_sessions_for_user(user).filter(overtime_status=OvertimeStatusChoices.PENDING)


def monitor_minutes_summary_for_user(user):
    return (
        visible_sessions_for_user(user)
        .values("monitor__id", "monitor__full_name", "monitor__codigo_estudiante")
        .annotate(
            normal_minutes_total=Sum("normal_minutes"),
            overtime_minutes_total=Sum("overtime_minutes"),
            penalty_minutes_total=Sum("penalty_minutes"),
        )
        .order_by("monitor__full_name")
    )

