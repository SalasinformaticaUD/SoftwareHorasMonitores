from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.common.choices import UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin, AdminRequiredMixin, paginate_collection
from apps.monitors.models import Monitor
from apps.schedules.forms import ScheduleBulkUploadForm, ScheduleExceptionForm, ScheduleForm
from apps.schedules.selectors import visible_schedule_exceptions_for_user
from apps.schedules.models import Schedule
from apps.schedules.services import (
    delete_schedule,
    delete_schedule_exception,
    import_schedule_rows_from_workbook,
    save_schedule,
    save_schedule_exception,
)


class ScheduleAdminView(AdminRequiredMixin, TemplateView):
    template_name = "admin_portal/schedules/index.html"
    paginate_by = 12
    sort_fields = {
        "monitor": "monitor__full_name",
        "day": "weekday",
        "start": "start_time",
        "location": "location",
    }

    def _schedule_queryset(self):
        queryset = Schedule.objects.select_related("monitor", "monitor__user")
        search = self.request.GET.get("q", "").strip()
        monitor_id = self.request.GET.get("monitor", "").strip()
        day = self.request.GET.get("day", "").strip()
        status = self.request.GET.get("status", "").strip()
        sort = self.request.GET.get("sort", "monitor")
        direction = self.request.GET.get("direction", "asc")

        if search:
            queryset = queryset.filter(
                Q(monitor__full_name__icontains=search)
                | Q(monitor__codigo_estudiante__icontains=search)
                | Q(monitor__user__email__icontains=search)
                | Q(location__icontains=search)
            )
        if monitor_id:
            queryset = queryset.filter(monitor_id=monitor_id)
        if day != "":
            queryset = queryset.filter(weekday=day)
        if status == "active":
            queryset = queryset.filter(is_active=True)
        elif status == "inactive":
            queryset = queryset.filter(is_active=False)

        sort_field = self.sort_fields.get(sort, "monitor__full_name")
        if direction == "desc":
            sort_field = f"-{sort_field}"
        return queryset.order_by(sort_field, "weekday", "start_time")

    def _selected_schedule(self):
        schedule_id = self.request.GET.get("edit") or self.request.POST.get("schedule_id")
        if not schedule_id:
            return None
        return get_object_or_404(Schedule.objects.select_related("monitor"), pk=schedule_id)

    def _calendar_context(self):
        monitors = Monitor.objects.select_related("user").filter(is_active=True).order_by("full_name")
        selected_monitor_id = self.request.GET.get("calendar_monitor") or self.request.GET.get("monitor")
        selected_monitor = monitors.filter(pk=selected_monitor_id).first() if selected_monitor_id else monitors.first()
        schedules = []
        if selected_monitor:
            schedules = Schedule.objects.filter(
                monitor=selected_monitor,
                is_active=True,
                weekday__lte=Schedule.Weekday.SATURDAY,
            ).order_by("weekday", "start_time")

        day_labels = [{"value": value, "label": label} for value, label in Schedule.Weekday.choices[:6]]
        blocks = []
        day_start_minutes = 6 * 60
        day_end_minutes = 22 * 60
        total_minutes = day_end_minutes - day_start_minutes
        for schedule in schedules:
            start = schedule.start_time.hour * 60 + schedule.start_time.minute
            end = schedule.end_time.hour * 60 + schedule.end_time.minute
            top = max((start - day_start_minutes) / total_minutes * 100, 0)
            height = max((end - start) / total_minutes * 100, 5)
            blocks.append(
                {
                    "item": schedule,
                    "day": schedule.weekday,
                    "style": f"top: {top:.2f}%; height: {height:.2f}%;",
                }
            )
        return {
            "calendar_monitors": monitors,
            "calendar_monitor": selected_monitor,
            "calendar_days": day_labels,
            "calendar_blocks": blocks,
            "calendar_hours": range(6, 23, 2),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editing_schedule = kwargs.get("editing_schedule")
        if editing_schedule is None:
            editing_schedule = self._selected_schedule()
        monitors = Monitor.objects.select_related("user").filter(is_active=True).order_by("full_name")
        queryset = self._schedule_queryset()
        pagination = paginate_collection(self.request, queryset, per_page=self.paginate_by)
        context.update(
            {
                "form": kwargs.get("form") or ScheduleForm(instance=editing_schedule, monitors=monitors),
                "upload_form": kwargs.get("upload_form") or ScheduleBulkUploadForm(),
                "upload_result": kwargs.get("upload_result"),
                "editing_schedule": editing_schedule,
                "monitors": monitors,
                "schedules": pagination["page_obj"].object_list,
                "day_choices": Schedule.Weekday.choices[:6],
                "stats": {
                    "total": Schedule.objects.count(),
                    "active": Schedule.objects.filter(is_active=True).count(),
                    "inactive": Schedule.objects.filter(is_active=False).count(),
                    "monitors": Monitor.objects.filter(schedules__isnull=False).distinct().count(),
                },
                **pagination,
                **self._calendar_context(),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "save")
        if action == "upload":
            form = ScheduleBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = import_schedule_rows_from_workbook(uploaded_file=form.cleaned_data["source_file"])
                    messages.success(request, f"Carga procesada: {result.created} horarios creados.")
                    return self.render_to_response(self.get_context_data(upload_form=form, upload_result=result))
                except ValidationError as exc:
                    form.add_error("source_file", "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(upload_form=form))

        if action == "delete":
            schedule = get_object_or_404(Schedule, pk=request.POST.get("schedule_id"))
            delete_schedule(schedule=schedule)
            messages.success(request, "Horario eliminado correctamente.")
            return redirect("admin-schedules")

        instance = None
        if request.POST.get("schedule_id"):
            instance = get_object_or_404(Schedule, pk=request.POST.get("schedule_id"))
        monitors = Monitor.objects.filter(is_active=True).order_by("full_name")
        form = ScheduleForm(request.POST, instance=instance, monitors=monitors)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, editing_schedule=instance))
        try:
            save_schedule(instance=instance, **form.cleaned_data)
            messages.success(request, "Horario guardado correctamente.")
            return redirect("admin-schedules")
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(form=form, editing_schedule=instance))


class ScheduleExceptionListView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "schedules/exceptions.html"

    @staticmethod
    def _exception_status(*, exception, today):
        if not exception.is_active:
            return {
                "label": "Inactiva",
                "badge_class": "text-bg-dark",
                "description": "La excepción está desactivada y no afecta sesiones.",
            }
        if exception.start_date <= today <= exception.end_date:
            return {
                "label": "Vigente",
                "badge_class": "text-bg-success",
                "description": "La excepción está activa y hoy sí aplica dentro del rango.",
            }
        if exception.start_date > today:
            return {
                "label": "Programada",
                "badge_class": "text-bg-secondary",
                "description": "La excepción está activa, pero todavía no ha empezado.",
            }
        return {
            "label": "Activa",
            "badge_class": "text-bg-primary",
            "description": "La excepción sigue activa en el sistema, aunque su rango de fechas ya terminó.",
        }

    def _selected_exception(self):
        exception_id = self.request.GET.get("edit") or self.request.POST.get("exception_id")
        if not exception_id:
            return None
        return get_object_or_404(visible_schedule_exceptions_for_user(self.request.user), pk=exception_id)

    def _can_manage_exception(self, exception) -> bool:
        if self.request.user.role == UserRoleChoices.ADMIN:
            return True
        return exception.department == self.request.user.department

    def _build_form(self, *, instance=None, data=None):
        return ScheduleExceptionForm(data=data, instance=instance, actor=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editing_exception = kwargs.get("editing_exception")
        if editing_exception is None:
            editing_exception = self._selected_exception()
        context["form"] = kwargs.get("form") or self._build_form(instance=editing_exception)
        context["editing_exception"] = editing_exception
        context["today"] = timezone.localdate()
        exceptions = [
            {
                "item": exception,
                "can_manage": self._can_manage_exception(exception),
                "scope_label": exception.get_department_display() if exception.department else "Todas las dependencias",
                "status": self._exception_status(exception=exception, today=context["today"]),
            }
            for exception in visible_schedule_exceptions_for_user(self.request.user)
        ]
        context["exceptions"] = exceptions
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "save")
        if action == "delete":
            exception = get_object_or_404(visible_schedule_exceptions_for_user(request.user), pk=request.POST.get("exception_id"))
            try:
                updated_sessions = delete_schedule_exception(actor=request.user, exception=exception)
                message = "Excepción eliminada."
                if updated_sessions:
                    message += f" Se recalcularon {updated_sessions} sesiones."
                messages.success(request, message)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            return redirect("schedule-exceptions")

        instance = None
        if request.POST.get("exception_id"):
            instance = get_object_or_404(
                visible_schedule_exceptions_for_user(request.user),
                pk=request.POST.get("exception_id"),
            )
        form = self._build_form(instance=instance, data=request.POST)
        if not form.is_valid():
            return self.render_to_response(self.get_context_data(form=form, editing_exception=instance))

        try:
            exception, updated_sessions = save_schedule_exception(
                actor=request.user,
                instance=instance,
                **form.cleaned_data,
            )
            action_label = "actualizada" if instance else "creada"
            message = f"Excepción {action_label} correctamente."
            if updated_sessions:
                message += f" Se recalcularon {updated_sessions} sesiones."
            messages.success(request, message)
            return redirect("schedule-exceptions")
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(form=form, editing_exception=instance))
