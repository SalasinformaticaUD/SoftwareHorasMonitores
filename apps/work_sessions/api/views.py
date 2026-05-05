from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import decorators, exceptions, response, status, viewsets

from apps.common.permissions import IsAdminOrLeader
from apps.work_sessions.api.serializers import OvertimeDecisionSerializer, WorkSessionSerializer
from apps.work_sessions.selectors import visible_sessions_for_user
from apps.work_sessions.services import review_overtime


class WorkSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkSessionSerializer
    permission_classes = [IsAdminOrLeader]

    def get_queryset(self):
        return visible_sessions_for_user(self.request.user)

    @decorators.action(detail=True, methods=["post"], url_path="review-overtime")
    def review_overtime_action(self, request, pk=None):
        session = self.get_object()
        serializer = OvertimeDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            review_overtime(
                session=session,
                reviewer=request.user,
                decision=serializer.validated_data["decision"],
                note=serializer.validated_data.get("note", ""),
                penalize_on_reject=serializer.validated_data.get("penalize_on_reject", True),
            )
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(WorkSessionSerializer(session).data, status=status.HTTP_200_OK)
