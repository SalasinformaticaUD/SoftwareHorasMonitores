from rest_framework import serializers

from apps.reports.models import MonitorMemorandum


class MonitorMemorandumSerializer(serializers.ModelSerializer):
    monitor_name = serializers.CharField(source="monitor.full_name", read_only=True)
    codigo_estudiante = serializers.CharField(source="monitor.codigo_estudiante", read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = MonitorMemorandum
        fields = ("id", "monitor", "monitor_name", "codigo_estudiante", "late_count_threshold", "sent_to", "sent_at", "pdf_url", "created_at")

    def get_pdf_url(self, obj):
        if not obj.pdf_file:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(obj.pdf_file.url) if request else obj.pdf_file.url


class GenerateCommitmentActSerializer(serializers.Serializer):
    monitor_id = serializers.UUIDField()


class HistoricalReportQuerySerializer(serializers.Serializer):
    department = serializers.CharField(required=False, allow_blank=True)
    semester_id = serializers.UUIDField(required=False)


class CommitmentActStatusSerializer(serializers.Serializer):
    monitor = serializers.UUIDField(source="monitor.id")
    monitor_name = serializers.CharField(source="monitor.full_name")
    codigo_estudiante = serializers.CharField(source="monitor.codigo_estudiante")
    has_signed = serializers.BooleanField()
    signed_file_name = serializers.CharField()
    uploaded_at = serializers.DateTimeField(allow_null=True)
    submission_id = serializers.UUIDField(source="submission.id", allow_null=True)
    status = serializers.CharField()
    rejection_reason = serializers.CharField()
    reviewed_at = serializers.DateTimeField(source="submission.reviewed_at", allow_null=True)


class CommitmentActUploadSerializer(serializers.Serializer):
    signed_file = serializers.FileField()

    def validate_signed_file(self, value):
        if not value.name.lower().endswith(".pdf"):
            raise serializers.ValidationError("El acta firmada debe ser un archivo PDF.")
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("El archivo PDF no puede superar 10 MB.")
        return value


class CommitmentActReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("accept", "reject"))
    rejection_reason = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs.get("rejection_reason", "").strip():
            attrs["rejection_reason"] = "Acta rechazada para corrección y nuevo envío."
        return attrs
