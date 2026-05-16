from django.contrib import admin, messages
from django.core.exceptions import ValidationError

from apps.reports.models import MonitorMemorandum, MonitorReportSnapshot
from apps.reports.services import send_lateness_memorandum


@admin.register(MonitorReportSnapshot)
class MonitorReportSnapshotAdmin(admin.ModelAdmin):
    list_display = ("monitor", "start_date", "end_date", "total_minutes", "has_memorandum")
    list_filter = ("department", "has_memorandum")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante")


@admin.register(MonitorMemorandum)
class MonitorMemorandumAdmin(admin.ModelAdmin):
    list_display = ("monitor", "late_count_threshold", "sent_to", "sent_at", "created_at")
    list_filter = ("sent_at", "late_count_threshold")
    search_fields = ("monitor__full_name", "monitor__codigo_estudiante", "sent_to")
    readonly_fields = ("created_at", "updated_at", "sent_at")
    actions = ("resend_selected_memorandums",)

    @admin.action(description="Reenviar memorandos seleccionados")
    def resend_selected_memorandums(self, request, queryset):
        sent = 0
        skipped = 0
        for memorandum in queryset.select_related("monitor", "monitor__user"):
            try:
                send_lateness_memorandum(memorandum=memorandum)
                sent += 1
            except ValidationError as exc:
                skipped += 1
                self.message_user(
                    request,
                    f"{memorandum.monitor}: {'; '.join(exc.messages)}",
                    level=messages.WARNING,
                )
        if sent:
            self.message_user(request, f"Memorandos reenviados: {sent}.", level=messages.SUCCESS)
        if skipped and not sent:
            self.message_user(request, "No se pudo reenviar ningun memorando.", level=messages.WARNING)
