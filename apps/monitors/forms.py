from django import forms
from django.contrib.auth import get_user_model

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices
from apps.monitors.models import Monitor


User = get_user_model()


def _apply_bootstrap(field):
    if isinstance(field.widget, forms.Select):
        field.widget.attrs["class"] = "form-select"
    else:
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (existing + " form-control").strip()


class MonitorRegistrationForm(forms.Form):
    full_name = forms.CharField(label="Nombre completo", max_length=255)
    codigo_estudiante = forms.CharField(label="Codigo estudiantil", max_length=20)
    email = forms.EmailField(label="Correo institucional")
    department = forms.ChoiceField(label="Dependencia", choices=DepartmentChoices.choices)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            _apply_bootstrap(field)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return email

    def clean_codigo_estudiante(self):
        code = self.cleaned_data["codigo_estudiante"].strip()
        if Monitor.objects.filter(codigo_estudiante__iexact=code).exists():
            raise forms.ValidationError("Ya existe un monitor con este codigo.")
        return code


class MonitorBulkUploadForm(forms.Form):
    source_file = forms.FileField(label="Archivo Excel (.xlsx)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self.fields["source_file"])

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file
