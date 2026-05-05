from django import forms

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.schedules.models import ScheduleException


class ScheduleImportForm(forms.Form):
    source_file = forms.FileField(label="Archivo de horarios")

    def clean_source_file(self):
        source_file = self.cleaned_data["source_file"]
        validate_excel_extension(source_file.name)
        return source_file


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
            self.fields["department"].help_text = (
                "Déjalo vacío para que la excepción aplique a todas las dependencias."
            )

    def clean_department(self):
        department = self.cleaned_data.get("department")
        if self.actor and self.actor.role != UserRoleChoices.ADMIN:
            return self.actor.department
        return department or None
