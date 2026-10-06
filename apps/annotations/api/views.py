from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import exceptions, viewsets
from rest_framework.permissions import IsAuthenticated

from apps.annotations.api.serializers import AnnotationSerializer
from apps.annotations.selectors import visible_annotations_for_user
from apps.annotations.services import delete_annotation
from apps.common.permissions import IsAdminOrLeader


class AnnotationViewSet(viewsets.ModelViewSet):
    serializer_class = AnnotationSerializer
    permission_classes = [IsAdminOrLeader]

    def get_permissions(self):
        # Los monitores pueden consultar exclusivamente sus propias anotaciones.
        # Las operaciones que modifican información conservan la restricción
        # administrativa para administradores y líderes.
        if self.action in {"list", "retrieve"}:
            return [IsAuthenticated()]
        return [IsAdminOrLeader()]

    def get_queryset(self):
        queryset = visible_annotations_for_user(self.request.user)
        monitoring_id = self.request.query_params.get("monitor")
        if monitoring_id:
            queryset = queryset.filter(monitor_id=monitoring_id)
        return queryset

    def perform_destroy(self, instance):
        try:
            delete_annotation(actor=self.request.user, annotation=instance)
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
