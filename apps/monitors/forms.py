from django import forms
from django.contrib.auth import get_user_model

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import Monitor, PROJECT_CHOICES


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
    numero_documento = forms.CharField(label="Numero de documento", max_length=32, required=False)
    email = forms.EmailField(label="Correo institucional")
    proyecto_curricular = forms.ChoiceField(
        label="Proyecto curricular",
        choices=(("", "Seleccione un proyecto curricular"), *PROJECT_CHOICES),
        required=False,
    )
    telefono = forms.CharField(label="Telefono", max_length=32, required=False)
    department = forms.ChoiceField(label="Dependencia", choices=DepartmentChoices.choices)

    def __init__(self, *args, actor=None, instance=None, **kwargs):
        self.actor = actor
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance and not self.is_bound:
            self.initial.update(
                {
                    "full_name": instance.full_name,
                    "codigo_estudiante": instance.codigo_estudiante,
                    "numero_documento": instance.numero_documento,
                    "email": instance.user.email if instance.user else "",
                    "proyecto_curricular": instance.proyecto_curricular,
                    "telefono": instance.telefono,
                    "department": instance.department,
                }
            )
        for field in self.fields.values():
            _apply_bootstrap(field)
        if actor and actor.role != UserRoleChoices.ADMIN:
            self.fields["department"].choices = [
                choice for choice in DepartmentChoices.choices if choice[0] == actor.department
            ]
            self.fields["department"].initial = actor.department
            self.fields["department"].help_text = "Como lider, solo puedes registrar monitores de tu dependencia."

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        users = User.objects.filter(email__iexact=email) | User.objects.filter(username__iexact=email)
        if self.instance and self.instance.user_id:
            users = users.exclude(pk=self.instance.user_id)
        non_monitor_user = users.exclude(role=UserRoleChoices.MONITOR).first()
        if non_monitor_user:
            raise forms.ValidationError("Ya existe una cuenta no monitor con este correo.")
        active_monitor = Monitor.objects.filter(user__in=users, is_active=True)
        if self.instance:
            active_monitor = active_monitor.exclude(pk=self.instance.pk)
        if active_monitor.exists():
            raise forms.ValidationError("Ya existe un monitor activo con este correo.")
        return email

    def clean_codigo_estudiante(self):
        code = self.cleaned_data["codigo_estudiante"].strip()
        monitors = Monitor.objects.filter(codigo_estudiante__iexact=code, is_active=True)
        if self.instance:
            monitors = monitors.exclude(pk=self.instance.pk)
        if monitors.exists():
            raise forms.ValidationError("Ya existe un monitor activo con este codigo.")
        return code

    def clean_department(self):
        department = self.cleaned_data["department"]
        if self.actor and self.actor.role != UserRoleChoices.ADMIN:
            return self.actor.department
        return department


class MonitorBulkUploadForm(forms.Form):
    source_file = forms.FileField(label="Archivo Excel (.xlsx)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self.fields["source_file"])

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file


class SemesterResetConfirmationForm(forms.Form):
    new_semester_name = forms.CharField(
        label="Nuevo semestre academico",
        max_length=20,
        initial="2026-3",
        help_text="Ejemplo: 2026-3",
    )
    password = forms.CharField(
        label="Contrasena del administrador",
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, *args, admin_user=None, **kwargs):
        self.admin_user = admin_user
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self.fields["new_semester_name"])
        _apply_bootstrap(self.fields["password"])

    def clean_new_semester_name(self):
        value = self.cleaned_data["new_semester_name"].strip()
        if not value:
            raise forms.ValidationError("Ingresa el semestre nuevo.")
        return value

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not self.admin_user or not self.admin_user.check_password(password):
            raise forms.ValidationError("La contrasena no coincide con tu cuenta de administrador.")
        return password

class MonitorActaCompromisoUploadForm(forms.Form):
    source_file = forms.FileField(label="Acta de compromiso (PDF)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap(self.fields["source_file"])

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        if not source_file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("El archivo debe ser un PDF.")
        return source_file
