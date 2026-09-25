from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.schedules.models import Schedule, ScheduleException
from apps.monitors.models import AcademicSemester


class ScheduleSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)

    class Meta:
        model = Schedule
        fields = (
            "id",
            "monitor",
            "monitor_name",
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

    def validate(self, attrs):
        data = {
            "monitor": attrs.get("monitor", getattr(self.instance, "monitor", None)),
            "weekday": attrs.get("weekday", getattr(self.instance, "weekday", None)),
            "start_time": attrs.get("start_time", getattr(self.instance, "start_time", None)),
            "end_time": attrs.get("end_time", getattr(self.instance, "end_time", None)),
            "asignatura": attrs.get("asignatura", getattr(self.instance, "asignatura", "")),
            "grupo": attrs.get("grupo", getattr(self.instance, "grupo", "")),
            "docente": attrs.get("docente", getattr(self.instance, "docente", "")),
            "proyecto_curricular": attrs.get(
                "proyecto_curricular", getattr(self.instance, "proyecto_curricular", "")
            ),
            "location": attrs.get("location", getattr(self.instance, "location", "")),
            "is_active": attrs.get("is_active", getattr(self.instance, "is_active", True)),
        }
        schedule = Schedule(**data)
        if self.instance:
            # `full_clean()` ejecuta también las validaciones de unicidad.
            # Al construir una instancia temporal Django la marca como nueva
            # (`_state.adding=True`) y termina detectando el propio registro
            # como duplicado. Marcarla como existente permite que excluya su
            # PK al validar una edición.
            schedule.pk = self.instance.pk
            schedule._state.adding = False
            schedule._state.db = self.instance._state.db
        try:
            schedule.full_clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


class ScheduleExceptionSerializer(serializers.ModelSerializer):
    department_label = serializers.CharField(source="get_department_display", read_only=True)

    class Meta:
        model = ScheduleException
        fields = (
            "id",
            "name",
            "description",
            "monitors",
            "schedules",
            "all_semester",
            "semester",
            "start_date",
            "end_date",
            "department",
            "department_label",
            "ignore_lateness",
            "approve_overtime",
            "is_active",
        )
        extra_kwargs = {"semester": {"read_only": True}, "start_date": {"required": False}, "end_date": {"required": False}}

    def validate(self, attrs):
        monitors = attrs.get("monitors", getattr(self.instance, "monitors", None))
        schedules = attrs.get("schedules", getattr(self.instance, "schedules", None))
        if monitors is not None and schedules is not None:
            monitor_ids = {monitor.pk for monitor in monitors.all()} if hasattr(monitors, "all") else {monitor.pk for monitor in monitors}
            schedule_items = schedules.all() if hasattr(schedules, "all") else schedules
            if any(schedule.monitor_id not in monitor_ids for schedule in schedule_items):
                raise serializers.ValidationError({"schedules": "Cada bloque debe pertenecer a uno de los usuarios seleccionados."})
        if attrs.get("all_semester", getattr(self.instance, "all_semester", False)):
            semester = AcademicSemester.objects.filter(is_active=True).first()
            if semester is None or not semester.starts_on or not semester.ends_on:
                raise serializers.ValidationError({"all_semester": "El semestre activo debe tener fechas configuradas."})
            attrs["semester"] = semester
            attrs["start_date"] = semester.starts_on
            attrs["end_date"] = semester.ends_on
        elif not attrs.get("start_date", getattr(self.instance, "start_date", None)) or not attrs.get("end_date", getattr(self.instance, "end_date", None)):
            raise serializers.ValidationError("Ingresa las fechas de inicio y finalización.")
        else:
            attrs["semester"] = None
        return attrs
