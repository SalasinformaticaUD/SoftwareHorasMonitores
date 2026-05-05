from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.views import View
from django.views.generic import FormView, TemplateView

from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin, enforce_public_lookup_limit
from apps.monitors.selectors import visible_monitors_for_user
from apps.reports.forms import PublicMonitorLookupForm
from apps.reports.selectors import (
    build_dashboard_context,
    monitor_lookup_result,
    public_monitor_lookup,
)
from apps.reports.services import export_department_dashboard_to_excel, get_dashboard_export_directory


class LeaderDashboardView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "dashboard/leader_dashboard_v2.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        context["dashboard_export_directory"] = str(get_dashboard_export_directory())
        return context


class MonitorRecordsDetailView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "dashboard/monitor_records.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        monitor = visible_monitors_for_user(self.request.user).filter(pk=self.kwargs["monitor_id"], is_active=True).first()
        if monitor is None:
            raise Http404("Monitor no encontrado.")
        context["result"] = monitor_lookup_result(monitor=monitor)
        return context


class DepartmentDashboardExportView(AdminOrLeaderRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        department = kwargs["department"]
        valid_departments = {choice[0] for choice in DepartmentChoices.choices}
        if department not in valid_departments:
            raise Http404("Dependencia no encontrada.")
        if request.user.role != UserRoleChoices.ADMIN and request.user.department != department:
            raise PermissionDenied("No puedes exportar otra dependencia.")

        export_path = export_department_dashboard_to_excel(user=request.user, department=department)
        return FileResponse(
            export_path.open("rb"),
            as_attachment=True,
            filename=export_path.name,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )


class PublicMonitorLookupView(FormView):
    template_name = "public/monitor_lookup.html"
    form_class = PublicMonitorLookupForm

    def form_valid(self, form):
        try:
            enforce_public_lookup_limit(self.request)
        except PermissionDenied as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        result = public_monitor_lookup(
            codigo_estudiante=form.cleaned_data["codigo_estudiante"],
        )
        context = self.get_context_data(form=form, result=result)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("result", None)
        return context
