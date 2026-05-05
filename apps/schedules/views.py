from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.common.choices import UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin
from apps.schedules.forms import ScheduleExceptionForm
from apps.schedules.selectors import visible_schedule_exceptions_for_user
from apps.schedules.services import delete_schedule_exception, save_schedule_exception


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
