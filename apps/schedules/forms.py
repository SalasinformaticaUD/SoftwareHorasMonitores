from django import forms

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import Monitor, PROJECT_CHOICES
from apps.schedules.models import Schedule, ScheduleException


class ScheduleImportForm(forms.Form):
    source_file = forms.FileField(label="Archivo de horarios")

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file


class ScheduleBulkUploadForm(forms.Form):
    source_file = forms.FileField(label="Archivo Excel (.xlsx)")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["source_file"].widget.attrs["class"] = "form-control"

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file


class ScheduleForm(forms.ModelForm):
    weekday = forms.ChoiceField(label="Dia", choices=Schedule.Weekday.choices[:6])

    class Meta:
        model = Schedule
        fields = (
            "monitor",
            "weekday",
            "start_time",
            "end_time",
            "asignatura",
            "grupo",
            "docente",
            "proyecto_curricular",
            "location",
            "is_active",
        )
        widgets = {
            "start_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
            "end_time": forms.TimeInput(format="%H:%M", attrs={"type": "time"}),
        }
        labels = {
            "monitor": "Monitor",
            "weekday": "Dia",
            "start_time": "Hora inicio",
            "end_time": "Hora fin",
            "asignatura": "Asignatura",
            "grupo": "Grupo",
            "docente": "Docente",
            "proyecto_curricular": "Proyecto curricular",
            "location": "Ubicacion",
            "is_active": "Activo",
        }

    def __init__(self, *args, monitors=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_time"].input_formats = ["%H:%M", "%H:%M:%S"]
        self.fields["end_time"].input_formats = ["%H:%M", "%H:%M:%S"]
        self.fields["monitor"].queryset = monitors or Monitor.objects.filter(is_active=True).order_by("full_name")
        self.fields["proyecto_curricular"].choices = (("", "Seleccione un proyecto curricular"), *PROJECT_CHOICES)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"

    def clean_weekday(self):
        return int(self.cleaned_data["weekday"])

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get("start_time")
        end_time = cleaned_data.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "La hora fin debe ser posterior a la hora inicio.")
        return cleaned_data


class ScheduleExceptionForm(forms.ModelForm):
    class Meta:
        model = ScheduleException
        fields = (
            "name",
            "description",
            "start_date",
            "end_date",
            "department",
            "ignore_lateness",
            "approve_overtime",
            "is_active",
        )
        widgets = {
            "start_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "end_date": forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "name": "Nombre de la excepción",
            "description": "Descripción",
            "start_date": "Fecha inicial",
            "end_date": "Fecha final",
            "department": "Dependencia",
            "ignore_lateness": "No contar retrasos",
            "approve_overtime": "Contar horas extra",
            "is_active": "Activa",
        }

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].input_formats = ["%Y-%m-%d"]
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (existing + " form-select").strip()
            else:
                existing = field.widget.attrs.get("class", "")
                field.widget.attrs["class"] = (existing + " form-control").strip()
        self.fields["department"].required = False
        self.fields["department"].empty_label = "Todas las dependencias"

        if actor and actor.role != UserRoleChoices.ADMIN:
            self.fields["department"].choices = [
                choice for choice in DepartmentChoices.choices if choice[0] == actor.department
            ]
            self.fields["department"].initial = actor.department
            self.fields["department"].help_text = "Como líder, solo puedes crear excepciones para tu dependencia."
        else:
            self.fields["department"].choices = [("", "Todas las dependencias")] + list(DepartmentChoices.choices)

    def clean_department(self):
        department = self.cleaned_data.get("department")
        if self.actor and self.actor.role != UserRoleChoices.ADMIN:
            return self.actor.department
        return department or None
