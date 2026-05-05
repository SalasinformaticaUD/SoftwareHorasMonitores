from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import FormView, TemplateView

from apps.attendance.forms import AttendanceUploadForm
from apps.attendance.models import AttendanceRawRecord
from apps.attendance.selectors import pending_reconciliation_records_for_user
from apps.attendance.services import assign_monitor_manually, create_import_job
from apps.attendance.tasks import process_import_job
from apps.common.choices import UserRoleChoices
from apps.common.web import AdminOrLeaderRequiredMixin
from apps.monitors.models import Monitor


class AttendanceImportView(AdminOrLeaderRequiredMixin, FormView):
    template_name = "attendance/upload.html"
    form_class = AttendanceUploadForm

    def form_valid(self, form):
        try:
            job = create_import_job(uploaded_file=form.cleaned_data["file"], uploaded_by=self.request.user)
            process_import_job.delay(str(job.id))
            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
                job.refresh_from_db()
                skipped_rows = max(job.total_rows - job.imported_rows - job.failed_rows, 0)
                if job.failed_rows:
                    messages.warning(
                        self.request,
                        (
                            f"Archivo procesado. Importadas: {job.imported_rows}, "
                            f"omitidas: {skipped_rows}, con error: {job.failed_rows}."
                        ),
                    )
                elif job.imported_rows == 0 and skipped_rows:
                    messages.info(
                        self.request,
                        (
                            "Archivo procesado, pero no se agregaron registros nuevos. "
                            f"Se omitieron {skipped_rows} filas porque ya existian."
                        ),
                    )
                else:
                    messages.success(
                        self.request,
                        (
                            f"Archivo procesado. Importadas: {job.imported_rows}, "
                            f"omitidas: {skipped_rows}, con error: {job.failed_rows}."
                        ),
                    )
            else:
                messages.success(self.request, "Archivo cargado. La importacion quedo en cola.")
        except ValidationError as exc:
            messages.error(self.request, "; ".join(exc.messages))
        return redirect("attendance-upload")


class ReconciliationQueueView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "attendance/reconciliation_queue.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        records = pending_reconciliation_records_for_user(self.request.user).order_by("-work_day", "raw_full_name")
        if self.request.user.role != UserRoleChoices.ADMIN:
            monitors = Monitor.objects.filter(department=self.request.user.department, is_active=True)
        else:
            monitors = Monitor.objects.filter(is_active=True)
        context["records"] = records
        context["monitor_options"] = monitors.order_by("full_name")
        return context

    def post(self, request, *args, **kwargs):
        raw_record = get_object_or_404(AttendanceRawRecord, pk=request.POST.get("raw_record_id"))
        monitor = get_object_or_404(Monitor, pk=request.POST.get("monitor_id"), is_active=True)
        try:
            assign_monitor_manually(raw_record=raw_record, monitor=monitor, actor=request.user)
            from apps.work_sessions.services import process_raw_record_to_session

            process_raw_record_to_session(raw_record=raw_record)
            messages.success(request, "Conciliacion manual aplicada y sesion generada.")
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        return redirect("attendance-reconciliation")
