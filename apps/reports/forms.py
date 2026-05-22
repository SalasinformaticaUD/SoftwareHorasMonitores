from django import forms


class PublicMonitorLookupForm(forms.Form):
    codigo_estudiante = forms.CharField(
        max_length=20,
        label="Codigo de estudiante",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Codigo de estudiante"}),
    )
