from rest_framework import serializers

from apps.annotations.models import Annotation
from apps.annotations.services import create_annotation, update_annotation


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = (
            "id",
            "leader",
            "monitor",
            "session",
            "department",
            "annotation_type",
            "description",
            "action",
            "delta_minutes",
            "occurred_on",
            "created_at",
        )
        read_only_fields = ("id", "leader", "department", "created_at")

    def create(self, validated_data):
        request = self.context["request"]
        return create_annotation(leader=request.user, **validated_data)

    def update(self, instance, validated_data):
        request = self.context["request"]
        payload = {
            "monitor": validated_data.get("monitor", instance.monitor),
            "annotation_type": validated_data.get("annotation_type", instance.annotation_type),
            "description": validated_data.get("description", instance.description),
            "action": validated_data.get("action", instance.action),
            "delta_minutes": validated_data.get("delta_minutes", instance.delta_minutes),
            "occurred_on": validated_data.get("occurred_on", instance.occurred_on),
            "session": validated_data.get("session", instance.session),
        }
        return update_annotation(actor=request.user, annotation=instance, **payload)
