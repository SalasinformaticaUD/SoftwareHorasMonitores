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
