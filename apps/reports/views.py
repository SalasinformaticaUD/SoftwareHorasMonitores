"""Vistas web para dashboard, consulta de monitores y reportes.

Este modulo define las pantallas principales de seguimiento de horas: tablero
de lider, detalle por monitor, exportacion a Excel, consulta por codigo y
consulta personal del monitor. Las vistas delegan calculos a selectores y
servicios para mantener separada la logica de presentacion.
"""

from django.contrib import messages
from datetime import datetime
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, TemplateView
from django.core.files.storage import FileSystemStorage
from django.db.models import Q


from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.common.utils import normalize_text
from apps.common.web import AdminOrLeaderRequiredMixin, MonitorRequiredMixin, enforce_public_lookup_limit, paginate_collection
from apps.monitors.selectors import visible_monitors_for_user
from apps.monitors.models import AcademicSemester, Monitor
from apps.reports.forms import PublicMonitorLookupForm
from apps.monitors.forms import MonitorActaCompromisoUploadForm
from apps.reports.selectors import (
    build_dashboard_context,
    monitor_lookup_result,
    public_monitor_lookup,
)
from apps.reports.pdf import build_monitor_commitment_act_pdf
from apps.reports.services import (
    build_commitment_act_status_rows,
    export_department_dashboard_to_excel,
    get_dashboard_export_directory,
    get_signed_commitment_acts_directory,
    send_lateness_memorandum,
    signed_commitment_act_for_monitor,
)
from apps.reports.models import MonitorMemorandum
from django.core.exceptions import ValidationError


class LeaderDashboardView(AdminOrLeaderRequiredMixin, TemplateView):
    """Muestra el dashboard administrativo para lideres y administradores.

    Funciones:
        - Cargar metricas visibles por rol.
        - Mostrar horas extra pendientes, registros recientes y notificaciones.
        - Exponer la ruta local donde se generan exportes Excel.
    """

    template_name = "dashboard/leader_dashboard_v2.html"

    def get_context_data(self, **kwargs):
        """Construye el contexto del dashboard.

        Args:
            **kwargs: Contexto base recibido desde ``TemplateView``.

        Returns:
            dict: Contexto con metricas, listados y directorio de exportacion.
        """
        context = super().get_context_data(**kwargs)
        context.update(build_dashboard_context(self.request.user))
        context["dashboard_export_directory"] = str(get_dashboard_export_directory())
        context["lookup_form"] = kwargs.get("lookup_form") or PublicMonitorLookupForm()
        context["lookup_submitted"] = kwargs.get("lookup_submitted", False)
        return context

    def post(self, request, *args, **kwargs):
        form = PublicMonitorLookupForm(request.POST)

        if form.is_valid():
            try:
                enforce_public_lookup_limit(request)
            except PermissionDenied as exc:
                messages.error(request, str(exc))
                return self.render_to_response(self.get_context_data(lookup_form=form, lookup_submitted=True))

            department = None if request.user.role == UserRoleChoices.ADMIN else request.user.department
            lookup_result = public_monitor_lookup(
                codigo_estudiante=form.cleaned_data["codigo_estudiante"],
                department=department,
            )
            if lookup_result:
                messages.success(request, f"Consulta exitosa para {lookup_result['monitor'].full_name}.")
                return redirect("dashboard-monitor-records", monitor_id=lookup_result["monitor"].id)
            else:
                messages.error(request, "No se encontro un monitor visible con ese codigo.")
        else:
            messages.error(request, "Ingresa un codigo de estudiante valido.")

        return self.render_to_response(
            self.get_context_data(
                lookup_form=form,
                lookup_submitted=True,
            )
        )


class MonitorRecordsDetailView(AdminOrLeaderRequiredMixin, TemplateView):
    """Muestra el detalle de registros de un monitor visible para el usuario.

    Funciones:
        - Validar que el monitor pertenezca al alcance del lider/admin.
        - Renderizar metricas, historial y linea de tiempo multinivel.
    """

    template_name = "dashboard/monitor_records.html"

    def get_context_data(self, **kwargs):
        """Construye el contexto del detalle de monitor.

        Args:
            **kwargs: Incluye ``monitor_id`` desde la URL.

        Returns:
            dict: Contexto con el resultado detallado del monitor.

        Raises:
            Http404: Si el monitor no existe o no es visible para el usuario.
        """
        context = super().get_context_data(**kwargs)
        monitor = visible_monitors_for_user(self.request.user).filter(pk=self.kwargs["monitor_id"], is_active=True).first()
        if monitor is None:
            raise Http404("Monitor no encontrado.")
        context["result"] = monitor_lookup_result(monitor=monitor)
        return context


class HistoricalRecordsView(AdminOrLeaderRequiredMixin, TemplateView):
    """Permite consultar historicos archivados por semestre."""

    template_name = "dashboard/historical_records.html"
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        semester_id = self.request.GET.get("semester", "").strip()
        query = self.request.GET.get("q", "").strip()
        monitors = (
            visible_monitors_for_user(self.request.user)
            .select_related("user", "semester")
            .filter(is_active=False)
            .order_by("-semester__starts_on", "department", "full_name")
        )
        if semester_id:
            monitors = monitors.filter(semester_id=semester_id)
        if query:
            monitors = monitors.filter(
                Q(full_name__icontains=query)
                | Q(codigo_estudiante__icontains=query)
                | Q(user__email__icontains=query)
            )
        pagination = paginate_collection(self.request, monitors, per_page=self.paginate_by)
        context.update(
            {
                "semesters": AcademicSemester.objects.filter(monitors__is_active=False)
                .distinct()
                .order_by("-starts_on", "-created_at"),
                "monitors": pagination["page_obj"].object_list,
                "filters": {"semester": semester_id, "q": query},
                **pagination,
            }
        )
        return context


class HistoricalMonitorRecordsDetailView(AdminOrLeaderRequiredMixin, TemplateView):
    """Muestra el detalle historico de un monitor archivado."""

    template_name = "dashboard/monitor_records.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        monitor = visible_monitors_for_user(self.request.user).filter(pk=self.kwargs["monitor_id"]).first()
        if monitor is None:
            raise Http404("Monitor no encontrado.")
        context["result"] = monitor_lookup_result(monitor=monitor)
        context["historical_mode"] = not monitor.is_active
        return context


class DepartmentDashboardExportView(AdminOrLeaderRequiredMixin, View):
    """Descarga el Excel consolidado de una dependencia.

    Funciones:
        - Validar la dependencia solicitada.
        - Respetar el alcance del lider por dependencia.
        - Entregar el archivo generado como descarga.
    """

    def get(self, request, *args, **kwargs):
        """Procesa la descarga del Excel por dependencia.

        Args:
            request: Peticion HTTP autenticada.
            *args: Argumentos posicionales de Django.
            **kwargs: Debe incluir ``department`` desde la URL.

        Returns:
            FileResponse: Archivo Excel generado para descarga.

        Raises:
            Http404: Si la dependencia no esta definida.
            PermissionDenied: Si un lider intenta exportar otra dependencia.
        """
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


class CommitmentActAdminView(AdminOrLeaderRequiredMixin, TemplateView):
    """Muestra el seguimiento administrativo de actas de compromiso.

    Funciones:
        - Cruzar monitores visibles con los PDFs firmados guardados en carpeta.
        - Filtrar por nombre, codigo, correo, dependencia y estado de firma.
        - Exponer acciones de descarga del acta generada y del acta firmada.
    """

    template_name = "admin_portal/commitment_acts/index.html"

    def get_context_data(self, **kwargs):
        """Construye el contexto del modulo de actas.

        Args:
            **kwargs: Contexto base de ``TemplateView``.

        Returns:
            dict: Contexto con filtros, estadisticas y filas paginadas.
        """

        context = super().get_context_data(**kwargs)
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        department = self.request.GET.get("department", "").strip()

        monitors = visible_monitors_for_user(self.request.user).select_related("user").filter(is_active=True)
        if query:
            monitors = monitors.filter(
                Q(full_name__icontains=query)
                | Q(codigo_estudiante__icontains=query)
                | Q(user__email__icontains=query)
            )
        if department and self.request.user.role == UserRoleChoices.ADMIN:
            monitors = monitors.filter(department=department)
        monitors = monitors.order_by("department", "full_name")

        rows = build_commitment_act_status_rows(monitors)
        signed_count = sum(1 for row in rows if row.has_signed)
        pending_count = len(rows) - signed_count
        if status == "signed":
            rows = [row for row in rows if row.has_signed]
        elif status == "pending":
            rows = [row for row in rows if not row.has_signed]

        pagination = paginate_collection(self.request, rows, per_page=20)
        context.update(
            {
                "rows": pagination["page_obj"].object_list,
                "page_obj": pagination["page_obj"],
                "page_param": pagination["page_param"],
                "page_query": pagination["page_query"],
                "stats": {
                    "total": signed_count + pending_count,
                    "signed": signed_count,
                    "pending": pending_count,
                },
                "departments": DepartmentChoices.choices,
                "filters": {
                    "q": query,
                    "status": status,
                    "department": department,
                },
            }
        )
        return context


class MemorandumAdminView(AdminOrLeaderRequiredMixin, TemplateView):
    """Lista memorandos generados y permite reenviarlos."""

    template_name = "reports/memorandums.html"
    paginate_by = 20

    def _base_queryset(self):
        visible_monitors = visible_monitors_for_user(self.request.user)
        queryset = MonitorMemorandum.objects.select_related("monitor", "monitor__user").filter(
            monitor__in=visible_monitors
        )
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        department = self.request.GET.get("department", "").strip()

        if query:
            queryset = queryset.filter(
                Q(monitor__full_name__icontains=query)
                | Q(monitor__codigo_estudiante__icontains=query)
                | Q(monitor__user__email__icontains=query)
                | Q(sent_to__icontains=query)
            )
        if department and self.request.user.role == UserRoleChoices.ADMIN:
            queryset = queryset.filter(monitor__department=department)
        if status == "sent":
            queryset = queryset.filter(sent_at__isnull=False)
        elif status == "pending":
            queryset = queryset.filter(sent_at__isnull=True)
        elif status == "missing_email":
            queryset = queryset.filter(Q(monitor__user__isnull=True) | Q(monitor__user__email=""))

        return queryset.order_by("-created_at", "monitor__full_name")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self._base_queryset()
        visible_queryset = MonitorMemorandum.objects.filter(monitor__in=visible_monitors_for_user(self.request.user))
        pagination = paginate_collection(self.request, queryset, per_page=self.paginate_by)
        context.update(
            {
                "memorandums": pagination["page_obj"].object_list,
                "departments": DepartmentChoices.choices,
                "filters": {
                    "q": self.request.GET.get("q", "").strip(),
                    "status": self.request.GET.get("status", "").strip(),
                    "department": self.request.GET.get("department", "").strip(),
                },
                "stats": {
                    "total": visible_queryset.count(),
                    "sent": visible_queryset.filter(sent_at__isnull=False).count(),
                    "pending": visible_queryset.filter(sent_at__isnull=True).count(),
                    "missing_email": visible_queryset.filter(
                        Q(monitor__user__isnull=True) | Q(monitor__user__email="")
                    ).count(),
                },
                **pagination,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        if request.POST.get("action") != "resend_memorandum":
            messages.error(request, "Accion no reconocida.")
            return redirect("memorandums-manage")

        memorandum = get_object_or_404(
            MonitorMemorandum.objects.select_related("monitor", "monitor__user").filter(
                monitor__in=visible_monitors_for_user(request.user)
            ),
            pk=request.POST.get("memorandum_id"),
        )
        try:
            send_lateness_memorandum(memorandum=memorandum)
            messages.success(request, "Memorando reenviado correctamente.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("memorandums-manage")


class GeneratedCommitmentActAdminDownloadView(AdminOrLeaderRequiredMixin, View):
    """Permite descargar el acta generada de un monitor visible.

    Funciones:
        - Validar alcance por rol/dependencia.
        - Generar el PDF con los datos actuales del monitor.
    """

    def get(self, request, *args, **kwargs):
        """Entrega el PDF generado del monitor solicitado.

        Args:
            request: Peticion HTTP autenticada.
            *args: Argumentos posicionales de Django.
            **kwargs: Debe incluir ``monitor_id``.

        Returns:
            HttpResponse: PDF generado como archivo adjunto.

        Raises:
            Http404: Si el monitor no existe dentro del alcance del usuario.
        """

        monitor = visible_monitors_for_user(request.user).select_related("user").filter(pk=kwargs["monitor_id"]).first()
        if monitor is None:
            raise Http404("Monitor no encontrado.")

        pdf_bytes = build_monitor_commitment_act_pdf(monitor=monitor, user=getattr(monitor, "user", None) or request.user)
        safe_name = normalize_text(monitor.full_name).replace(" ", "_")
        filename = f"Acta_Compromiso_{datetime.now().year}_{safe_name}_{monitor.codigo_estudiante}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class SignedCommitmentActAdminDownloadView(AdminOrLeaderRequiredMixin, View):
    """Permite descargar el PDF firmado almacenado en carpeta.

    Funciones:
        - Validar que el monitor sea visible para el usuario.
        - Buscar el PDF firmado asociado al codigo estudiantil.
        - Entregar el archivo sin permitir rutas arbitrarias.
    """

    def get(self, request, *args, **kwargs):
        """Entrega el acta firmada del monitor solicitado.

        Args:
            request: Peticion HTTP autenticada.
            *args: Argumentos posicionales de Django.
            **kwargs: Debe incluir ``monitor_id``.

        Returns:
            FileResponse: PDF firmado como archivo adjunto.

        Raises:
            Http404: Si no existe monitor visible o PDF firmado.
        """

        monitor = visible_monitors_for_user(request.user).filter(pk=kwargs["monitor_id"]).first()
        if monitor is None:
            raise Http404("Monitor no encontrado.")

        signed_file = signed_commitment_act_for_monitor(monitor)
        if signed_file is None or not signed_file.exists():
            raise Http404("Acta firmada no encontrada.")
        return FileResponse(
            signed_file.open("rb"),
            as_attachment=True,
            filename=signed_file.name,
            content_type="application/pdf",
        )


class SignedCommitmentActsBulkDownloadView(AdminOrLeaderRequiredMixin, View):
    """Descarga todas las actas firmadas visibles para el usuario.

    Funciones:
        - Respetar el alcance administrativo por rol y dependencia.
        - Buscar PDFs firmados asociados a monitores visibles.
        - Construir un archivo ZIP en memoria para descarga masiva.
    """

    def get(self, request, *args, **kwargs):
        """Entrega un ZIP con las actas firmadas disponibles.

        Args:
            request: Peticion HTTP autenticada.
            *args: Argumentos posicionales de Django.
            **kwargs: Argumentos nombrados de Django.

        Returns:
            HttpResponse: Archivo ZIP con PDFs firmados.

        Raises:
            Http404: Si no hay actas firmadas para descargar.
        """

        monitors = visible_monitors_for_user(request.user).select_related("user").filter(is_active=True)
        signed_rows = [row for row in build_commitment_act_status_rows(monitors) if row.has_signed]
        if not signed_rows:
            raise Http404("No hay actas firmadas para descargar.")

        buffer = BytesIO()
        used_names = set()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
            for row in signed_rows:
                safe_monitor = normalize_text(row.monitor.full_name).replace(" ", "_") or "monitor"
                arcname = f"{row.monitor.codigo_estudiante}_{safe_monitor}_{row.signed_file_name}"
                if arcname in used_names:
                    arcname = f"{row.monitor.id}_{arcname}"
                used_names.add(arcname)
                zip_file.write(row.signed_file, arcname=arcname)
        buffer.seek(0)

        filename = f"Actas_Compromiso_Firmadas_{datetime.now().year}.zip"
        response = HttpResponse(buffer.getvalue(), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class PublicMonitorLookupView(AdminOrLeaderRequiredMixin, FormView):
    """Permite a lideres/admin consultar horas de un monitor por codigo.

    Funciones:
        - Validar codigo estudiantil mediante formulario.
        - Aplicar limite de consultas.
        - Restringir resultados a la dependencia del lider.
    """

    template_name = "public/monitor_lookup.html"
    form_class = PublicMonitorLookupForm
    permission_denied_message = "La consulta por codigo esta disponible solo para administradores y lideres."

    def form_valid(self, form):
        """Resuelve la consulta cuando el formulario es valido.

        Args:
            form: Formulario validado con ``codigo_estudiante``.

        Returns:
            HttpResponse: Pagina renderizada con el resultado o errores.
        """
        try:
            enforce_public_lookup_limit(self.request)
        except PermissionDenied as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        department = None if self.request.user.role == UserRoleChoices.ADMIN else self.request.user.department
        result = public_monitor_lookup(codigo_estudiante=form.cleaned_data["codigo_estudiante"], department=department)
        context = self.get_context_data(form=form, result=result)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        """Agrega metadatos de modo de consulta al contexto.

        Args:
            **kwargs: Contexto base y resultado opcional.

        Returns:
            dict: Contexto de template con ``lookup_mode``.
        """
        context = super().get_context_data(**kwargs)
        context.setdefault("result", None)
        context["lookup_mode"] = "leader"
        return context


class MonitorSelfHoursView(MonitorRequiredMixin, TemplateView):
    """Muestra la consulta personal de horas para usuarios monitor.

    Funciones:
        - Obtener el monitor vinculado al usuario autenticado.
        - Mostrar metricas, historial y linea de tiempo.
        - Permitir la descarga esperada y carga de acta de compromiso firmada.
    """

    template_name = "dashboard/monitor_self_hours.html"

    def get_context_data(self, **kwargs):
        """Construye el contexto de la pantalla personal del monitor.

        Args:
            **kwargs: Puede incluir formularios o resultados de carga.

        Returns:
            dict: Contexto con datos del monitor, formulario de acta y resultado
            de carga cuando exista.
        """
        context = super().get_context_data(**kwargs)
        profiles = list(
            Monitor.objects.filter(user=self.request.user)
            .select_related("semester")
            .order_by("-is_active", "-semester__starts_on", "-created_at")
        )
        selected_id = self.request.GET.get("monitor_id")
        monitor = next((profile for profile in profiles if str(profile.id) == selected_id), None)
        if monitor is None:
            monitor = next((profile for profile in profiles if profile.is_active), None) or (profiles[0] if profiles else None)
        proyecto = monitor.get_proyecto_curricular_display() if monitor and monitor.proyecto_curricular else None
        context["result"] = monitor_lookup_result(monitor=monitor) if monitor else None
        if context["result"]:
            context["result"]["año"] = datetime.now().year # Agregar año actual al resultado para usar en la plantilla
            context["result"]["monitor_name"] = monitor.full_name.replace(" ", "_")  # Agregar nombre completo del monitor al resultado para usar en la plantilla
            context["result"]["compromise_act_url"] = reverse("monitor-commitment-act-pdf")
            context["result"]["proyecto"] = proyecto
            context["result"]["profiles"] = profiles
            context["result"]["is_current_semester"] = bool(monitor.is_active)
        context.update(
            {
                "upload_form": kwargs.get("upload_form") or MonitorActaCompromisoUploadForm(),
                "upload_result": kwargs.get("upload_result"),
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Procesa la carga del acta de compromiso firmada.

        Args:
            request: Peticion HTTP con archivo PDF.
            *args: Argumentos posicionales de Django.
            **kwargs: Argumentos nombrados de Django.

        Returns:
            HttpResponse: Pagina renderizada con exito o errores del formulario.
        """
        action = self.request.POST.get("action")
        context=self.get_context_data()# Inicializar upload_result en el contexto
        name = context["result"]["monitor_name"].replace(" ", "_") if context["result"] else "monitor"
        if action == "upload":
            form = MonitorActaCompromisoUploadForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    result = form.cleaned_data["source_file"]
                    fs = FileSystemStorage(location=str(get_signed_commitment_acts_directory()))
                    filename = fs.save("Acta_Compromiso_"+str(context["result"]["año"])+"_"+name+"_"+str(context["result"]["monitor"].codigo_estudiante)+".pdf", result)
                    messages.success(request, f"Acta de compromiso procesada.")
                    return self.render_to_response(self.get_context_data(upload_form=form, upload_result=result))
                except ValidationError as exc:
                    form.add_error("source_file", "; ".join(exc.messages))
            return self.render_to_response(self.get_context_data(upload_form=form))


class MonitorCommitmentActPdfView(MonitorRequiredMixin, View):
    """Entrega el acta de compromiso generada para el monitor autenticado.

    Funciones:
        - Validar que el usuario tenga un perfil de monitor vinculado.
        - Generar el PDF personalizado en memoria.
        - Devolver el archivo como descarga.
    """

    def get(self, request, *args, **kwargs):
        """Genera y descarga el acta de compromiso del monitor autenticado.

        Args:
            request: Peticion HTTP del usuario monitor.
            *args: Argumentos posicionales de Django.
            **kwargs: Argumentos nombrados de Django.

        Returns:
            HttpResponse: Respuesta con contenido PDF y cabecera de descarga.

        Raises:
            Http404: Si el usuario monitor no tiene perfil vinculado.
        """
        monitor = getattr(request.user, "monitor_profile", None)
        if monitor is None:
            raise Http404("Monitor no encontrado.")

        pdf_bytes = build_monitor_commitment_act_pdf(monitor=monitor, user=request.user)
        safe_name = normalize_text(monitor.full_name).replace(" ", "_")
        filename = f"Acta_Compromiso_{datetime.now().year}_{safe_name}_{monitor.codigo_estudiante}.pdf"
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
