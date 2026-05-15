from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic import TemplateView

from apps.annotations.forms import AnnotationAdjustmentForm
from apps.annotations.selectors import visible_annotations_for_user
from apps.annotations.services import create_annotation, delete_annotation, update_annotation
from apps.attendance.selectors import visible_inconsistencies_for_user
from apps.attendance.services import link_annotation_to_inconsistency
from apps.common.web import AdminOrLeaderRequiredMixin


class AnnotationManagementView(AdminOrLeaderRequiredMixin, TemplateView):
    template_name = "annotations/manage.html"

    def _selected_annotation(self):
        annotation_id = self.request.GET.get("edit") or self.request.POST.get("annotation_id")
        if not annotation_id:
            return None
        return get_object_or_404(visible_annotations_for_user(self.request.user), pk=annotation_id)

    def _selected_inconsistency(self):
        inconsistency_id = self.request.GET.get("inconsistency") or self.request.POST.get("inconsistency_id")
        if not inconsistency_id:
            return None
        return get_object_or_404(visible_inconsistencies_for_user(self.request.user), pk=inconsistency_id)

    def _initial_from_inconsistency(self, inconsistency):
        if inconsistency is None or inconsistency.monitor_id is None:
            return {}
        return {
            "monitor": inconsistency.monitor_id,
            "annotation_type": self.request.GET.get("annotation_type") or "missing_punch",
            "occurred_on": inconsistency.work_day,
        }

    def _build_form(self, *, data=None, instance=None, inconsistency=None):
        initial = self._initial_from_inconsistency(inconsistency) if instance is None else None
        return AnnotationAdjustmentForm(data=data, actor=self.request.user, instance=instance, initial=initial)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        editing_annotation = kwargs.get("editing_annotation")
        if editing_annotation is None:
            editing_annotation = self._selected_annotation()
        source_inconsistency = kwargs.get("source_inconsistency")
        if source_inconsistency is None:
            source_inconsistency = self._selected_inconsistency()
        context["form"] = kwargs.get("form") or self._build_form(
            instance=editing_annotation,
            inconsistency=source_inconsistency,
        )
        context["editing_annotation"] = editing_annotation
        context["source_inconsistency"] = source_inconsistency
        context["recent_annotations"] = visible_annotations_for_user(self.request.user).order_by("-occurred_on", "-created_at")
        context["today"] = timezone.localdate()
        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action", "save")
        if action == "delete":
            annotation = get_object_or_404(
                visible_annotations_for_user(request.user),
                pk=request.POST.get("annotation_id"),
            )
            try:
                delete_annotation(actor=request.user, annotation=annotation)
                messages.success(request, "Anotación eliminada.")
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            return redirect("annotations-manage")

        annotation = self._selected_annotation()
        source_inconsistency = self._selected_inconsistency()
        form = self._build_form(data=request.POST, instance=annotation, inconsistency=source_inconsistency)
        if not form.is_valid():
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    editing_annotation=annotation,
                    source_inconsistency=source_inconsistency,
                )
            )

        try:
            if annotation is None:
                annotation = create_annotation(
                    leader=request.user,
                    monitor=form.cleaned_data["monitor"],
                    annotation_type=form.cleaned_data["annotation_type"],
                    description=form.cleaned_data["description"],
                    action=form.cleaned_data["action"],
                    delta_minutes=form.cleaned_data["delta_minutes"],
                    occurred_on=form.cleaned_data["occurred_on"],
                )
                direction = "agregaron" if annotation.delta_minutes > 0 else "descontaron"
                messages.success(
                    request,
                    f"Anotación registrada. Se {direction} {abs(annotation.delta_minutes) / 60:g} horas a {annotation.monitor.full_name}.",
                )
                if source_inconsistency is not None:
                    link_annotation_to_inconsistency(
                        inconsistency=source_inconsistency,
                        annotation=annotation,
                        actor=request.user,
                    )
                    messages.success(request, "Anotacion vinculada como solucion de la inconsistencia.")
                    return redirect("inconsistencies-manage")
            else:
                annotation = update_annotation(
                    actor=request.user,
                    annotation=annotation,
                    monitor=form.cleaned_data["monitor"],
                    annotation_type=form.cleaned_data["annotation_type"],
                    description=form.cleaned_data["description"],
                    action=form.cleaned_data["action"],
                    delta_minutes=form.cleaned_data["delta_minutes"],
                    occurred_on=form.cleaned_data["occurred_on"],
                )
                messages.success(request, "Anotación actualizada.")
            return redirect("annotations-manage")
        except ValidationError as exc:
            form.add_error(None, "; ".join(exc.messages))
            return self.render_to_response(
                self.get_context_data(
                    form=form,
                    editing_annotation=annotation,
                    source_inconsistency=source_inconsistency,
                )
            )
