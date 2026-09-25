from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.attendance.models import (
    AttendanceImportJob,
    AttendanceInconsistency,
    AttendanceInconsistencyEvent,
    AttendanceRawRecord,
)
from apps.attendance.selectors import (
    nearby_marks_for_inconsistency,
    nearby_schedules_for_inconsistency,
)
from apps.schedules.models import Schedule
from apps.work_sessions.models import WorkSession


class AttendanceImportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceImportJob
        fields = (
            "id",
            "file_name",
            "source_file",
            "status",
            "total_rows",
            "imported_rows",
            "failed_rows",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )
        read_only_fields = (
            "file_name",
            "status",
            "total_rows",
            "imported_rows",
            "failed_rows",
            "error_message",
            "created_at",
            "started_at",
            "finished_at",
        )


class AttendanceRawRecordSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)

    class Meta:
        model = AttendanceRawRecord
        fields = (
            "id",
            "import_job",
            "row_number",
            "raw_full_name",
            "raw_department",
            "raw_user_number",
            "raw_user_id",
            "work_day",
            "event_at",
            "entry_at",
            "exit_at",
            "record_type",
            "operation",
            "exception_description",
            "shift",
            "identification_code",
            "identification",
            "task_code",
            "device_number",
            "marked",
            "pairing_status",
            "paired_record",
            "duplicate_of",
            "paired_at",
            "pairing_reason",
            "monitor",
            "monitor_name",
            "reconciliation_status",
            "manual_review_reason",
            "processed_at",
            "processing_error",
        )
        read_only_fields = fields


class ManualAssignmentSerializer(serializers.Serializer):
    monitor_id = serializers.UUIDField()


class AttendanceInconsistencySerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True, allow_null=True)
    monitor_code = serializers.CharField(source="monitor.codigo_estudiante", read_only=True, allow_null=True)
    department = serializers.SerializerMethodField()
    department_label = serializers.SerializerMethodField()
    raw_full_name = serializers.CharField(source="raw_record.raw_full_name", read_only=True)
    raw_department = serializers.CharField(source="raw_record.raw_department", read_only=True)
    event_at = serializers.DateTimeField(source="raw_record.event_at", read_only=True, allow_null=True)
    pairing_status = serializers.CharField(source="raw_record.pairing_status", read_only=True)
    pairing_status_label = serializers.CharField(
        source="raw_record.get_pairing_status_display",
        read_only=True,
    )
    inconsistency_type_label = serializers.CharField(
        source="get_inconsistency_type_display",
        read_only=True,
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    weekday = serializers.SerializerMethodField()
    solution_annotation_description = serializers.CharField(
        source="solution_annotation.description", read_only=True, allow_null=True
    )
    solution_annotation_delta_minutes = serializers.IntegerField(
        source="solution_annotation.delta_minutes", read_only=True, allow_null=True
    )

    class Meta:
        model = AttendanceInconsistency
        fields = (
            "id",
            "raw_record",
            "monitor",
            "monitor_name",
            "monitor_code",
            "department",
            "department_label",
            "raw_full_name",
            "raw_department",
            "work_day",
            "weekday",
            "inconsistency_type",
            "inconsistency_type_label",
            "status",
            "status_label",
            "message",
            "resolution_note",
            "solution_annotation",
            "solution_annotation_description",
            "solution_annotation_delta_minutes",
            "event_at",
            "pairing_status",
            "pairing_status_label",
            "detected_at",
            "validated_at",
        )
        read_only_fields = fields

    def get_department(self, obj):
        return obj.monitor.department if obj.monitor_id else ""

    def get_department_label(self, obj):
        return obj.monitor.get_department_display() if obj.monitor_id else obj.raw_record.raw_department

    def get_weekday(self, obj):
        return Schedule.Weekday(obj.work_day.weekday()).label


class NearbyScheduleSerializer(serializers.ModelSerializer):
    weekday_label = serializers.CharField(source="get_weekday_display", read_only=True)
    project_label = serializers.CharField(
        source="get_proyecto_curricular_display",
        read_only=True,
    )
    assigned_minutes = serializers.SerializerMethodField()

    class Meta:
        model = Schedule
        fields = (
            "id",
            "weekday",
            "weekday_label",
            "start_time",
            "end_time",
            "assigned_minutes",
            "asignatura",
            "grupo",
            "docente",
            "proyecto_curricular",
            "project_label",
            "location",
        )
        read_only_fields = fields

    def get_assigned_minutes(self, obj):
        start = obj.start_time.hour * 60 + obj.start_time.minute
        end = obj.end_time.hour * 60 + obj.end_time.minute
        return max(end - start, 0)


class NearbyMarkSerializer(serializers.ModelSerializer):
    pairing_status_label = serializers.CharField(source="get_pairing_status_display", read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceRawRecord
        fields = (
            "id",
            "row_number",
            "event_at",
            "entry_at",
            "exit_at",
            "record_type",
            "operation",
            "pairing_status",
            "pairing_status_label",
            "paired_record",
            "duplicate_of",
            "pairing_reason",
            "reconciliation_status",
            "is_current",
        )
        read_only_fields = fields

    def get_is_current(self, obj):
        return obj.pk == self.context.get("current_raw_record_id")


class InconsistencyEventSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source="get_action_display", read_only=True)
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AttendanceInconsistencyEvent
        fields = ("id", "action", "action_label", "note", "actor", "actor_name", "created_at")
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.display_name if obj.actor_id else "Sistema"


class InconsistencyWorkSessionSerializer(serializers.ModelSerializer):
    schedule = NearbyScheduleSerializer(read_only=True)

    class Meta:
        model = WorkSession
        fields = (
            "id",
            "schedule",
            "actual_start",
            "actual_end",
            "normal_minutes",
            "overtime_minutes",
            "penalty_minutes",
            "late_minutes",
            "session_state",
            "invalidation_reason",
        )
        read_only_fields = fields


class AttendanceInconsistencyDetailSerializer(AttendanceInconsistencySerializer):
    nearby_schedules = serializers.SerializerMethodField()
    nearby_marks = serializers.SerializerMethodField()
    events = InconsistencyEventSerializer(many=True, read_only=True)
    work_session = serializers.SerializerMethodField()

    class Meta(AttendanceInconsistencySerializer.Meta):
        fields = AttendanceInconsistencySerializer.Meta.fields + (
            "nearby_schedules",
            "nearby_marks",
            "work_session",
            "events",
        )

    def get_nearby_schedules(self, obj):
        return NearbyScheduleSerializer(nearby_schedules_for_inconsistency(obj), many=True).data

    def get_nearby_marks(self, obj):
        return NearbyMarkSerializer(
            nearby_marks_for_inconsistency(obj),
            many=True,
            context={"current_raw_record_id": obj.raw_record_id},
        ).data

    def get_work_session(self, obj):
        try:
            session = obj.raw_record.work_session
        except ObjectDoesNotExist:
            return None
        return InconsistencyWorkSessionSerializer(session).data


class InconsistencySolutionSerializer(serializers.Serializer):
    annotation_type = serializers.ChoiceField(
        choices=("missing_punch", "virtual_hours", "permission", "novelty")
    )
    action = serializers.ChoiceField(choices=("add", "deduct", "note"))
    delta_minutes = serializers.IntegerField(min_value=-1440, max_value=1440)
    description = serializers.CharField(max_length=2000)


class InconsistencyInvalidationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
