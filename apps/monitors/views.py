from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.common.choices import UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin, paginate_collection
from apps.monitors.forms import MonitorBulkUploadForm, MonitorRegistrationForm
from apps.monitors.models import Monitor
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import (
    create_monitor_with_user,
    delete_monitor_account,
    import_monitors_from_workbook,
    resend_monitor_activation,
    set_monitor_account_active,
)


class MonitorAdminView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "admin_portal/monitors/index.html"
    paginate_by = 12

    sort_fields = {
        "name": "full_name",
        "code": "codigo_estudiante",
        "email": "user__email",
        "department": "department",
    }

    def _base_queryset(self):
        queryset = visible_monitors_for_user(self.request.user).select_related("user").order_by("full_name")
        search = self.request.GET.get("q", "").strip()
        department = self.request.GET.get("department", "").strip()
        status = self.request.GET.get("status", "").strip()
        sort = self.request.GET.get("sort", "name")
        direction = self.request.GET.get("direction", "asc")

        if search:
            queryset = queryset.filter(
                Q(full_name__icontains=search)
                | Q(codigo_estudiante__icontains=search)
                | Q(user__email__icontains=search)
            )
        if department:
            queryset = queryset.filter(department=department)
        if status == "active":
            queryset = queryset.filter(is_active=True, user__is_active=True).exclude(user__password__startswith="!")
        elif status == "pending":
            queryset = queryset.filter(is_active=True, user__is_active=True, user__password__startswith="!")
        elif status == "inactive":
            queryset = queryset.filter(Q(is_active=False) | Q(user__is_active=False))

        sort_field = self.sort_fields.get(sort, "full_name")
        if direction == "desc":
            sort_field = f"-{sort_field}"
        return queryset.order_by(sort_field, "full_name")

    @staticmethod
    def _account_status(monitor):
        if not monitor.is_active or (monitor.user and not monitor.user.is_active):
            return {"label": "Inactiva", "badge_class": "text-bg-dark"}
        if monitor.user and monitor.user.has_usable_password():
            return {"label": "Activa", "badge_class": "text-bg-primary"}
        return {"label": "Pendiente", "badge_class": "text-bg-warning"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self._base_queryset()
        pagination = paginate_collection(self.request, queryset, per_page=self.paginate_by)
        monitors = [
            {
                "item": monitor,
                "email": monitor.user.email if monitor.user else "-",
                "status": self._account_status(monitor),
            }
            for monitor in pagination["page_obj"].object_list
        ]
        context.update(
            {
                "create_form": kwargs.get("create_form") or MonitorRegistrationForm(actor=self.request.user),
                "upload_form": kwargs.get("upload_form") or MonitorBulkUploadForm(),
                "upload_result": kwargs.get("upload_result"),
                "monitors": monitors,
                "stats": {
                    "total": visible_monitors_for_user(self.request.user).count(),
                    "active": visible_monitors_for_user(self.request.user)
                    .filter(is_active=True, user__is_active=True)
                    .exclude(user__password__startswith="!")
                    .count(),
                    "pending": visible_monitors_for_user(self.request.user)
                    .filter(is_active=True, user__is_active=True, user__password__startswith="!")
                    .count(),
                    "inactive": visible_monitors_for_user(self.request.user)
                    .filter(Q(is_active=False) | Q(user__is_active=False))
                    .count(),
                },
                "is_admin_scope": self.request.user.role == UserRoleChoices.ADMIN,
                **pagination,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "create")
        if action == "create":
            form = MonitorRegistrationForm(request.POST, actor=request.user)
            if form.is_valid():
                create_monitor_with_user(**form.cleaned_data, request=request, actor=request.user)
                messages.success(request, "Monitor creado. Se envio el correo de activacion.")
                return redirect("admin-monitors")
            return self.render_to_response(self.get_context_data(create_form=form))

        if action == "upload":
            form = MonitorBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = import_monitors_from_workbook(
                        uploaded_file=form.cleaned_data["source_file"],
                        request=request,
                        actor=request.user,
                    )
                    messages.success(request, f"Carga procesada: {result.created} monitores creados.")
                    return self.render_to_response(self.get_context_data(upload_form=form, upload_result=result))
                except ValidationError as exc:
                    form.add_error("source_file", "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(upload_form=form))

        monitor = get_object_or_404(
            visible_monitors_for_user(request.user).select_related("user"),
            pk=request.POST.get("monitor_id"),
        )
        if request.user.role != UserRoleChoices.ADMIN and monitor.department != request.user.department:
            raise PermissionDenied("No puedes gestionar monitores de otra dependencia.")
        if action == "toggle":
            is_active = request.POST.get("is_active") == "1"
            set_monitor_account_active(monitor=monitor, is_active=is_active)
            messages.success(request, "Estado del monitor actualizado.")
        elif action == "resend":
            try:
                sent = resend_monitor_activation(monitor=monitor, request=request)
                if sent:
                    messages.success(request, "Correo de activacion reenviado.")
                else:
                    messages.warning(request, "No fue posible preparar el correo de activacion.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        elif action == "delete":
            delete_monitor_account(monitor=monitor)
            messages.success(request, "Monitor eliminado correctamente.")
        return redirect("admin-monitors")
