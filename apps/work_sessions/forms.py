from django import forms

from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices


class OvertimeReviewForm(forms.Form):
    session_id = forms.UUIDField(widget=forms.HiddenInput)
    decision = forms.ChoiceField(choices=(("approve", "Aprobar"), ("reject", "Rechazar")))
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), required=False, label="Anotación")


class InvalidateWorkSessionForm(forms.Form):
    session_id = forms.UUIDField(widget=forms.HiddenInput)
    reason = forms.CharField(
        label="Motivo de invalidacion",
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )


class SessionAnnotationForm(forms.Form):
    session_id = forms.UUIDField(widget=forms.HiddenInput)
    annotation_type = forms.ChoiceField(
        choices=AnnotationTypeChoices.choices,
        label="Tipo",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    action = forms.ChoiceField(
        choices=(
            (AnnotationActionChoices.ADD, "Agregar horas"),
            (AnnotationActionChoices.DEDUCT, "Descontar horas"),
            (AnnotationActionChoices.NOTE, "Solo anotar"),
        ),
        label="Accion",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    hours = forms.DecimalField(
        decimal_places=2,
        max_digits=6,
        min_value=0,
        required=False,
        label="Horas",
        widget=forms.NumberInput(attrs={"step": "0.25", "min": "0", "class": "form-control"}),
    )
    description = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        hours = cleaned_data.get("hours") or 0
        minutes = int(hours * 60)
        if action != AnnotationActionChoices.NOTE and minutes <= 0:
            raise forms.ValidationError("Los ajustes de horas deben ser mayores que cero.")
        if action == AnnotationActionChoices.NOTE:
            minutes = 0
        elif action == AnnotationActionChoices.DEDUCT:
            minutes = -minutes
        cleaned_data["delta_minutes"] = minutes
        return cleaned_data

