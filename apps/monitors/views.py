from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView

from apps.common.choices import UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin, AdminRequiredMixin, paginate_collection
from apps.monitors.forms import MonitorBulkUploadForm, MonitorRegistrationForm, SemesterResetConfirmationForm
from apps.monitors.models import Monitor
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.services import (
    create_monitor_with_user,
    delete_monitor_account,
    import_monitors_from_workbook,
    reset_semester_data,
    resend_monitor_activation,
    semester_reset_preview_counts,
    set_monitor_account_active,
    update_monitor_with_user,
)
from apps.reports.models import MonitorMemorandum
from apps.reports.services import refresh_lateness_memorandum_pdf, send_lateness_memorandum


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
        queryset = (
            visible_monitors_for_user(self.request.user)
            .select_related("user")
            .prefetch_related("memorandums")
            .annotate(
                late_arrivals_count=Count(
                    "work_sessions",
                    filter=(
                        Q(work_sessions__is_late=True, work_sessions__lateness_excused=False)
                        & ~Q(work_sessions__session_state="invalid")
                    ),
                    distinct=True,
                ),
                memorandums_count=Count("memorandums", distinct=True),
            )
            .order_by("full_name")
        )
        search = self.request.GET.get("q", "").strip()
        department = self.request.GET.get("department", "").strip()
        status = self.request.GET.get("status", "").strip()
        alerts = self.request.GET.get("alerts", "").strip()
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
        else:
            queryset = queryset.filter(is_active=True)
        if alerts == "memorandums":
            queryset = queryset.filter(memorandums_count__gt=0)
        elif alerts == "late":
            queryset = queryset.filter(late_arrivals_count__gt=0)

        sort_field = self.sort_fields.get(sort, "full_name")
        if direction == "desc":
            sort_field = f"-{sort_field}"
        return queryset.order_by(sort_field, "full_name")

    @staticmethod
    def _account_status(monitor):
        if not monitor.is_active or (monitor.user and not monitor.user.is_active):
            return {"label": "Inactivo", "badge_class": "text-bg-dark"}
        if monitor.user and monitor.user.has_usable_password():
            return {"label": "Activo", "badge_class": "text-bg-primary"}
        return {"label": "Pendiente", "badge_class": "text-bg-warning"}

    def _selected_monitor(self):
        monitor_id = self.request.GET.get("edit") or self.request.POST.get("monitor_id")
        if not monitor_id:
            return None
        return get_object_or_404(
            visible_monitors_for_user(self.request.user).select_related("user"),
            pk=monitor_id,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editing_monitor = kwargs.get("editing_monitor")
        if editing_monitor is None:
            editing_monitor = self._selected_monitor()
        queryset = self._base_queryset()
        pagination = paginate_collection(self.request, queryset, per_page=self.paginate_by)
        monitors = [
            {
                "item": monitor,
                "email": monitor.user.email if monitor.user else "-",
                "status": self._account_status(monitor),
                "late_count": getattr(monitor, "late_arrivals_count", 0),
                "memorandum_count": getattr(monitor, "memorandums_count", 0),
                "memorandums": list(monitor.memorandums.all()),
            }
            for monitor in pagination["page_obj"].object_list
        ]
        context.update(
            {
                "create_form": kwargs.get("create_form")
                or MonitorRegistrationForm(actor=self.request.user, instance=editing_monitor),
                "editing_monitor": editing_monitor,
                "upload_form": kwargs.get("upload_form") or MonitorBulkUploadForm(),
                "upload_result": kwargs.get("upload_result"),
                "monitors": monitors,
                "stats": {
                    "total": visible_monitors_for_user(self.request.user).filter(is_active=True).count(),
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
                try:
                    create_monitor_with_user(**form.cleaned_data, request=request, actor=request.user)
                    messages.success(request, "Monitor creado. Se reutilizo la cuenta existente si tenia historial.")
                    return redirect("admin-monitors")
                except ValidationError as exc:
                    form.add_error(None, "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(create_form=form))

        if action == "update":
            monitor = self._selected_monitor()
            form = MonitorRegistrationForm(request.POST, actor=request.user, instance=monitor)
            if form.is_valid():
                try:
                    update_monitor_with_user(monitor=monitor, **form.cleaned_data, request=request, actor=request.user)
                    messages.success(request, "Monitor actualizado correctamente.")
                    return redirect("admin-monitors")
                except ValidationError as exc:
                    form.add_error(None, "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(create_form=form, editing_monitor=monitor))

        if action == "upload":
            form = MonitorBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = import_monitors_from_workbook(
                        uploaded_file=form.cleaned_data["source_file"],
                        request=request,
                        actor=request.user,
                        confirm_repeating_monitors=form.cleaned_data["confirm_repeating_monitors"],
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
        elif action == "resend_memorandum":
            memorandum = get_object_or_404(
                MonitorMemorandum.objects.select_related("monitor", "monitor__user").filter(monitor=monitor),
                pk=request.POST.get("memorandum_id"),
            )
            try:
                send_lateness_memorandum(memorandum=memorandum)
                messages.success(request, "Memorando reenviado correctamente.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
        elif action == "delete":
            delete_monitor_account(monitor=monitor)
            messages.success(request, "Monitor eliminado correctamente.")
        return redirect("admin-monitors")


class MonitorMemorandumDownloadView(AdminOrLeaderRequiredMixin, View):
    """Descarga un PDF de memorando de un monitor visible para el usuario.

    Funciones:
        - Validar alcance de admin/lider sobre el monitor.
        - Entregar el PDF asociado al memorando sin permitir acceso cruzado.
    """

    def get(self, request, *args, **kwargs):
        """Retorna el PDF del memorando solicitado.

        Args:
            request: Peticion HTTP autenticada.
            *args: Argumentos posicionales de Django.
            **kwargs: Incluye ``monitor_id`` y ``memorandum_id`` desde la URL.

        Returns:
            FileResponse: Archivo PDF del memorando.

        Raises:
            Http404: Si el monitor, memorando o archivo no existe en el alcance.
        """

        monitor = get_object_or_404(
            visible_monitors_for_user(request.user),
            pk=kwargs["monitor_id"],
        )
        memorandum = get_object_or_404(
            MonitorMemorandum.objects.filter(monitor=monitor),
            pk=kwargs["memorandum_id"],
        )
        try:
            refresh_lateness_memorandum_pdf(memorandum=memorandum)
        except ValidationError as exc:
            raise Http404("; ".join(exc.messages)) from exc
        if not memorandum.pdf_file:
            raise Http404("El memorando no tiene PDF asociado.")
        try:
            handle = memorandum.pdf_file.open("rb")
        except FileNotFoundError as exc:
            raise Http404("El archivo del memorando no existe.") from exc
        filename = memorandum.pdf_file.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return FileResponse(handle, as_attachment=False, filename=filename, content_type="application/pdf")


class SemesterResetView(AdminRequiredMixin, TemplateView):
    """Permite a un administrador iniciar un semestre nuevo."""

    template_name = "admin_portal/monitors/semester_reset.html"

    reset_items = (
        ("monitors", "Monitores activos que pasan a historico"),
        ("monitor_users", "Cuentas de monitor conservadas"),
        ("schedules", "Horarios archivados"),
        ("schedule_exceptions", "Excepciones conservadas"),
        ("attendance_import_jobs", "Cargas de asistencia conservadas"),
        ("attendance_raw_records", "Registros importados conservados"),
        ("work_sessions", "Registros procesados y horas extra conservados"),
        ("attendance_inconsistencies", "Inconsistencias conservadas"),
        ("annotations", "Anotaciones conservadas"),
        ("report_snapshots", "Reportes generados conservados"),
        ("memorandums", "Memorandos conservados"),
        ("notifications", "Notificaciones que se limpiaran"),
    )

    def _count_rows(self):
        counts = semester_reset_preview_counts()
        return [{"key": key, "label": label, "count": counts.get(key, 0)} for key, label in self.reset_items]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "form": kwargs.get("form") or SemesterResetConfirmationForm(admin_user=self.request.user),
                "count_rows": self._count_rows(),
                "reset_attempted": kwargs.get("reset_attempted", False),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        form = SemesterResetConfirmationForm(request.POST, admin_user=request.user)
        if not form.is_valid():
            messages.error(request, "No se pudo confirmar la accion. Revisa la contrasena.")
            return self.render_to_response(self.get_context_data(form=form, reset_attempted=True))

        try:
            result = reset_semester_data(new_semester_name=form.cleaned_data["new_semester_name"])
        except ValidationError as exc:
            form.add_error("new_semester_name", "; ".join(exc.messages))
            messages.error(request, "No se pudo iniciar el semestre nuevo.")
            return self.render_to_response(self.get_context_data(form=form, reset_attempted=True))
        archived_total = sum(result.deleted_counts.values())
        messages.success(
            request,
            "Semestre {0} archivado y semestre {1} iniciado. Se conservaron {2} registros historicos.".format(
                result.archived_semester.name,
                result.new_semester.name,
                archived_total,
            ),
        )
        return redirect("admin-monitors")
