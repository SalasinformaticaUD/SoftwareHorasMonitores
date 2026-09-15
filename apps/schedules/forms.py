from django import forms

from apps.attendance.validators import validate_excel_extension
from apps.common.choices import DepartmentChoices, UserRoleChoices
from apps.monitors.models import AcademicSemester, Monitor, PROJECT_CHOICES
from apps.monitors.selectors import visible_current_monitors_for_user
from apps.schedules.models import Schedule, ScheduleException


class ScheduleMultipleSelect(forms.SelectMultiple):
    """Expone el monitor dueño de cada bloque para el filtrado dependiente."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, "instance", None)
        if instance is not None:
            option["attrs"]["data-monitor-id"] = str(instance.monitor_id)
        return option


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
    start_time = forms.TimeField(
        label="Hora inicio",
        input_formats=["%H:%M", "%H:%M:%S"],
        widget=forms.TimeInput(
            format="%H:%M",
            attrs={
                "type": "time",
                "placeholder": "HH:MM",
                "min": "00:00",
                "max": "23:59",
                "step": "60",
                "lang": "es-CO",
                "autocomplete": "off",
            }
        ),
        error_messages={"invalid": "Usa hora militar en formato HH:MM, por ejemplo 18:00."},
    )
    end_time = forms.TimeField(
        label="Hora fin",
        input_formats=["%H:%M", "%H:%M:%S"],
        widget=forms.TimeInput(
            format="%H:%M",
            attrs={
                "type": "time",
                "placeholder": "HH:MM",
                "min": "00:00",
                "max": "23:59",
                "step": "60",
                "lang": "es-CO",
                "autocomplete": "off",
            }
        ),
        error_messages={"invalid": "Usa hora militar en formato HH:MM, por ejemplo 22:00."},
    )

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
            "monitors",
            "schedules",
            "all_semester",
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
            "monitors": forms.SelectMultiple(
                attrs={
                    "class": "exception-multi-source",
                    "data-placeholder": "Seleccionar usuarios",
                    "data-empty": "No hay usuarios disponibles",
                    "data-select-all": "true",
                }
            ),
            "schedules": ScheduleMultipleSelect(
                attrs={
                    "class": "exception-multi-source",
                    "data-placeholder": "Seleccionar bloques",
                    "data-empty": "Selecciona primero uno o varios usuarios",
                }
            ),
        }
        labels = {
            "name": "Nombre de la excepción",
            "description": "Descripción",
            "monitors": "Usuarios incluidos",
            "schedules": "Bloques horarios",
            "all_semester": "Todo el semestre académico",
            "start_date": "Fecha inicial",
            "end_date": "Fecha final",
            "department": "Dependencia",
            "ignore_lateness": "No contar retrasos",
            "approve_overtime": "Aprobar horas extra automaticamente",
            "is_active": "Activa",
        }

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        self.fields["start_date"].input_formats = ["%Y-%m-%d"]
        self.fields["end_date"].input_formats = ["%Y-%m-%d"]
        self.fields["start_date"].required = False
        self.fields["end_date"].required = False
        monitors = (
            visible_current_monitors_for_user(actor)
            if actor is not None
            else Monitor.objects.filter(is_active=True, semester__is_active=True)
        ).select_related("user", "semester").order_by("full_name")
        self.fields["monitors"].queryset = monitors
        self.fields["monitors"].required = True
        self.fields["monitors"].help_text = "Selecciona uno o varios usuarios específicos."
        self.fields["schedules"].queryset = Schedule.objects.filter(
            monitor__in=monitors,
            is_active=True,
        ).select_related("monitor").order_by("monitor__full_name", "weekday", "start_time")
        self.fields["schedules"].required = True
        self.fields["schedules"].help_text = "Solo se aplicará en los bloques seleccionados."
        self.fields["all_semester"].help_text = "Las fechas se tomarán del semestre académico activo."
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

    def clean(self):
        cleaned_data = super().clean()
        monitors = cleaned_data.get("monitors")
        schedules = cleaned_data.get("schedules")
        if monitors is not None and schedules is not None:
            selected_monitor_ids = set(monitors.values_list("pk", flat=True))
            unrelated = [schedule for schedule in schedules if schedule.monitor_id not in selected_monitor_ids]
            if unrelated:
                self.add_error("schedules", "Cada bloque debe pertenecer a uno de los usuarios seleccionados.")

        if cleaned_data.get("all_semester"):
            semester = AcademicSemester.objects.filter(is_active=True).first()
            if semester is None:
                self.add_error("all_semester", "No hay un semestre académico activo configurado.")
            elif not semester.starts_on or not semester.ends_on:
                self.add_error(
                    "all_semester",
                    "El semestre activo debe tener fechas de inicio y finalización configuradas.",
                )
            else:
                cleaned_data["semester"] = semester
                cleaned_data["start_date"] = semester.starts_on
                cleaned_data["end_date"] = semester.ends_on
                self.instance.semester = semester
        else:
            cleaned_data["semester"] = None
            self.instance.semester = None
            if not cleaned_data.get("start_date"):
                self.add_error("start_date", "Ingresa la fecha inicial.")
            if not cleaned_data.get("end_date"):
                self.add_error("end_date", "Ingresa la fecha final.")
        return cleaned_data
