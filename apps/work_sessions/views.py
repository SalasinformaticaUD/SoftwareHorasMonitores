from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from apps.common.web import AdminOrLeaderRequiredMixin
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
