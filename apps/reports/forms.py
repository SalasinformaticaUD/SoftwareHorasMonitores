from django import forms


class CommitmentActRejectionForm(forms.Form):
    reason = forms.CharField(label="Motivo del rechazo", max_length=1000, widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}))

    def clean_reason(self):
        reason = self.cleaned_data["reason"].strip()
        if not reason:
            raise forms.ValidationError("Indica el motivo del rechazo.")
        return reason


class PublicMonitorLookupForm(forms.Form):
    codigo_estudiante = forms.CharField(
        max_length=20,
        label="Codigo de estudiante",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Codigo de estudiante"}),
    )
