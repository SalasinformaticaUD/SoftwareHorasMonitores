from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.annotations.models import Annotation
from apps.attendance.models import AttendanceInconsistencyEvent, AttendanceRawRecord
from apps.attendance.selectors import (
    pending_inconsistencies_for_user,
    pending_reconciliation_records_for_user,
    visible_inconsistencies_for_user,
    visible_raw_records_for_user,
)
from apps.common.choices import (
    AnnotationActionChoices,
    AnnotationTypeChoices,
    AttendanceInconsistencyActionChoices,
    AttendanceInconsistencyStatusChoices,
    AttendanceInconsistencyTypeChoices,
)
from apps.attendance.services import (
    assign_monitor_manually,
    invalidate_inconsistent_raw_record,
    reject_raw_record,
)
from apps.common.web import AdminOrLeaderRequiredMixin
from apps.monitors.selectors import visible_monitors_for_user
from apps.schedules.models import Schedule
from apps.work_sessions.models import WorkSession
from apps.work_sessions.selectors import pending_overtime_sessions_for_user
from apps.work_sessions.services import review_overtime

class OvertimeReviewListView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "work_sessions/overtime_review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["sessions"] = pending_overtime_sessions_for_user(self.request.user).order_by("-work_day", "monitor__full_name")
        return context

    def post(self, request, *args, **kwargs):
        session = get_object_or_404(WorkSession, pk=request.POST.get("session_id"))
        try:
            review_overtime(
                session=session,
                reviewer=request.user,
                decision=request.POST.get("decision", ""),
                note=request.POST.get("note", ""),
                penalize_on_reject=request.POST.get("penalize_on_reject") == "on",
            )
            messages.success(request, "Revisión de horas extra registrada.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("overtime-review")


class InconsistencyManagementView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "work_sessions/inconsistencies.html"

    def _visible_raw_record(self, raw_record_id):
        return get_object_or_404(visible_raw_records_for_user(self.request.user), pk=raw_record_id)

    def _visible_inconsistency(self, inconsistency_id):
        return get_object_or_404(visible_inconsistencies_for_user(self.request.user), pk=inconsistency_id)

    @staticmethod
    def _marking_context_for_inconsistency(inconsistency):
        monitor = inconsistency.monitor
        if monitor is None:
            return []

        ### MOSTRAR LOS TRES DIAS ###
        # days = [inconsistency.work_day + timedelta(days=offset) for offset in (-1, 0, 1)]
        # records_by_day = {
        #     day: list(
        #         AttendanceRawRecord.objects.filter(
        #             monitor=monitor,
        #             work_day=day,
        #             event_at__isnull=False,
        #         )
        #         .select_related("paired_record", "duplicate_of")
        #         .order_by("event_at", "created_at")
        #     )
        #     for day in days
        # }
        # schedules_by_weekday = {
        #     weekday: list(
        #         Schedule.objects.filter(
        #             monitor=monitor,
        #             weekday=weekday,
        #             is_active=True,
        #         ).order_by("start_time", "end_time")
        #     )
        #     for weekday in {day.weekday() for day in days}
        # }
        # labels = {
        #     days[0]: "Dia anterior",
        #     days[1]: "Dia de la inconsistencia",
        #     days[2]: "Dia siguiente",
        # }
        # return [
        #     {
        #         "day": day,
        #         "label": labels[day],
        #         "records": records_by_day[day],
        #         "schedules": schedules_by_weekday.get(day.weekday(), []),
        #     }
        #     for day in days
        # ]

        ### MOSTRAR SOLO EL DIA DE LA INCONSISTENCIA ###    
        day = inconsistency.work_day

        records = list(
            AttendanceRawRecord.objects.filter(
                monitor=monitor,
                work_day=day,
                event_at__isnull=False,
            )
            .select_related("paired_record", "duplicate_of")
            .order_by("event_at", "created_at")
        )

        schedules = list(
            Schedule.objects.filter(
                monitor=monitor,
                weekday=day.weekday(),
                is_active=True,
            ).order_by("start_time", "end_time")
        )

        return {
            "day": day,
            "label": "Dia de la inconsistencia",
            "records": records,
            "schedules": schedules,
        }


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        raw_records = pending_reconciliation_records_for_user(self.request.user).order_by("-work_day", "raw_full_name")[:20]
        attendance_inconsistencies = pending_inconsistencies_for_user(self.request.user).order_by(
            "-work_day",
            "monitor__full_name",
            "-detected_at",
        )[:40]
        inconsistency_rows = [
            {
                "item": inconsistency,
                "marking_context": self._marking_context_for_inconsistency(inconsistency),
            }
            for inconsistency in attendance_inconsistencies
        ]
        visible_inconsistencies = visible_inconsistencies_for_user(self.request.user)
        recent_inconsistency_events = (
            AttendanceInconsistencyEvent.objects.select_related(
                "inconsistency",
                "inconsistency__raw_record",
                "inconsistency__monitor",
                "actor",
            )
            .filter(inconsistency__in=visible_inconsistencies)
            .exclude(
                Q(action=AttendanceInconsistencyActionChoices.DETECTED)
                | Q(
                    action=AttendanceInconsistencyActionChoices.AUTO_RESOLVED,
                    inconsistency__inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
                )
            )
            .order_by("-created_at")[:20]
        )
        resolved_duplicate_inconsistencies = visible_inconsistencies.filter(
            inconsistency_type=AttendanceInconsistencyTypeChoices.DUPLICATE_MARK,
            status=AttendanceInconsistencyStatusChoices.RESOLVED,
        ).order_by("-detected_at")[:20]
        context.update(
            {
                "raw_records": raw_records,
                "attendance_inconsistencies": attendance_inconsistencies,
                "inconsistency_rows": inconsistency_rows,
                "recent_inconsistency_events": recent_inconsistency_events,
                "resolved_duplicate_inconsistencies": resolved_duplicate_inconsistencies,
                "monitor_options": visible_monitors_for_user(self.request.user).filter(is_active=True).order_by("full_name"),
                "stats": {
                    "raw_pending": pending_reconciliation_records_for_user(self.request.user).count(),
                    "attendance_inconsistencies": pending_inconsistencies_for_user(self.request.user).count(),
                },
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "reconcile_raw":
            raw_record = self._visible_raw_record(request.POST.get("raw_record_id"))
            monitor = get_object_or_404(visible_monitors_for_user(request.user), pk=request.POST.get("monitor_id"), is_active=True)
            try:
                assign_monitor_manually(raw_record=raw_record, monitor=monitor, actor=request.user)
                messages.success(request, "Registro conciliado y reprocesado.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            return redirect("inconsistencies-manage")

        if action == "invalidate_inconsistent_raw":
            inconsistency = self._visible_inconsistency(request.POST.get("inconsistency_id"))
            # monitor = get_object_or_404(visible_monitors_for_user(request.user), pk=request.POST.get("monitor_id"), is_active=True)
            try:
                annotation = Annotation.objects.create(
                    leader=request.user,
                    monitor=inconsistency.monitor,
                    department=inconsistency.monitor.department,
                    annotation_type=AnnotationTypeChoices.MISSING_PUNCH,
                    description=(
                        "Inconsistencia invalidada. "
                        "No se contabilizan horas para este registro."
                    ),
                    action=AnnotationActionChoices.NOTE,
                    delta_minutes=0,
                    occurred_on=inconsistency.work_day,
                )
                inconsistency.solution_annotation = annotation
                inconsistency.save(update_fields=["solution_annotation"])
                print(inconsistency.solution_annotation)
                messages.success(
                    request,
                    "Registro inconsistente invalidado y anotación de 0 horas creada."
                )
                invalidate_inconsistent_raw_record(
                    inconsistency=inconsistency,
                    actor=request.user,
                    reason=request.POST.get("reason", ""),
                )
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            return redirect("inconsistencies-manage")

        if action == "reject_raw":
            raw_record = self._visible_raw_record(request.POST.get("raw_record_id"))
            try:
                reject_raw_record(raw_record=raw_record, actor=request.user, reason=request.POST.get("reason", ""))
                messages.success(request, "Registro crudo rechazado sin modificar la marcacion original.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            return redirect("inconsistencies-manage")

        messages.error(request, "Accion no reconocida.")
        return redirect("inconsistencies-manage")
