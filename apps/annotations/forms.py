from decimal import Decimal

from django import forms

from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices
from apps.monitors.models import Monitor
from apps.monitors.selectors import visible_monitors_for_user


class AnnotationAdjustmentForm(forms.Form):
    monitor = forms.ModelChoiceField(queryset=Monitor.objects.none(), label="Monitor")
    annotation_type = forms.ChoiceField(choices=AnnotationTypeChoices.choices, label="Tipo de anotación")
    action = forms.ChoiceField(
        choices=(
            (AnnotationActionChoices.ADD, "Agregar horas"),
            (AnnotationActionChoices.DEDUCT, "Descontar horas"),
        ),
        label="Acción",
    )
    hours = forms.DecimalField(
        decimal_places=2,
        max_digits=6,
        min_value=Decimal("0.01"),
        max_value=Decimal("24"),
        label="Horas a ajustar (h)",
        help_text="Usa valores positivos entre 0.01 y 24. El sistema convierte estas horas a minutos internamente.",
        widget=forms.NumberInput(attrs={"step": "0.25", "min": "0.01"}),
    )
    occurred_on = forms.DateField(
        label="Fecha de la novedad",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
    )
    description = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Describe por qué se suman o descuentan estas horas.",
    )

    def __init__(self, *args, actor=None, instance=None, **kwargs):
        self.actor = actor
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["monitor"].queryset = visible_monitors_for_user(actor).order_by("full_name") if actor else self.fields["monitor"].queryset
        for field in self.fields.values():
            if isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs["class"] = "form-control"
            else:
                field.widget.attrs["class"] = "form-control"
        if instance is not None and not self.is_bound:
            self.initial.update(
                {
                    "monitor": instance.monitor_id,
                    "annotation_type": instance.annotation_type,
                    "action": instance.action,
                    "hours": abs(instance.delta_minutes) / 60,
                    "occurred_on": instance.occurred_on,
                    "description": instance.description,
                }
            )

    def clean(self):
        cleaned_data = super().clean()
        hours = cleaned_data.get("hours")
        action = cleaned_data.get("action")
        if hours is None or not action:
            return cleaned_data
        minutes = int(hours * 60)
        if minutes <= 0:
            raise forms.ValidationError("El ajuste debe ser mayor que cero.")
        if action == AnnotationActionChoices.DEDUCT:
            minutes = -minutes
        cleaned_data["delta_minutes"] = minutes
        return cleaned_data
