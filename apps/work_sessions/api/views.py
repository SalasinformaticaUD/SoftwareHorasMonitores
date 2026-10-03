from datetime import date

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import decorators, exceptions, response, status, viewsets

from apps.common.pagination import OptionalPageNumberPagination
from apps.common.permissions import IsAdminOrLeader
from apps.monitors.selectors import visible_monitors_for_user
from apps.work_sessions.models import WorkSession
from apps.work_sessions.api.serializers import OvertimeDecisionSerializer, WorkSessionSerializer
from apps.work_sessions.selectors import visible_sessions_for_user
from apps.work_sessions.services import review_overtime, invalidate_work_session
from rest_framework import serializers


class WorkSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkSessionSerializer
    permission_classes = [IsAdminOrLeader]
    pagination_class = OptionalPageNumberPagination

    def get_queryset(self):
        return visible_sessions_for_user(self.request.user)

    def overtime_history_queryset(self):
        return WorkSession.objects.select_related(
            "monitor", "monitor__semester", "overtime_reviewed_by", "overtime_exception"
        ).filter(
            monitor__in=visible_monitors_for_user(self.request.user),
            overtime_status__in=("approved", "rejected"),
        )

    @decorators.action(detail=False, methods=["get"], url_path="overtime-history")
    def overtime_history(self, request):
        queryset = self.overtime_history_queryset()
        monitor = request.query_params.get("monitor", "").strip()
        if monitor:
            queryset = queryset.filter(Q(monitor__full_name__icontains=monitor) | Q(monitor__codigo_estudiante__icontains=monitor))

        work_day = request.query_params.get("work_day", "").strip()
        if work_day:
            try:
                parsed_day = date.fromisoformat(work_day)
            except ValueError as exc:
                raise exceptions.ValidationError({"work_day": "La fecha no es válida."}) from exc
            queryset = queryset.filter(work_day=parsed_day)

        decision = request.query_params.get("status", "").strip()
        if decision:
            if decision not in {"approved", "rejected"}:
                raise exceptions.ValidationError({"status": "La decisión no es válida."})
            queryset = queryset.filter(overtime_status=decision)

        semester = request.query_params.get("semester", "").strip()
        if semester == "__unassigned__":
            queryset = queryset.filter(monitor__semester__isnull=True)
        elif semester:
            queryset = queryset.filter(monitor__semester__name=semester)

        queryset = queryset.order_by("-work_day", "-actual_start", "-created_at", "-id")
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return response.Response(self.get_serializer(queryset, many=True).data)

    @decorators.action(detail=False, methods=["get"], url_path="overtime-semesters")
    def overtime_semesters(self, request):
        queryset = self.overtime_history_queryset()
        names = queryset.exclude(monitor__semester__isnull=True).order_by(
            "monitor__semester__name"
        ).values_list("monitor__semester__name", flat=True).distinct()
        options = list(names)
        if queryset.filter(monitor__semester__isnull=True).exists():
            options.append("__unassigned__")
        return response.Response(options)

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

    @decorators.action(detail=True, methods=["post"], url_path="invalidate")
    def invalidate_action(self, request, pk=None):
        session = self.get_object()
        reason = request.data.get("reason", "").strip()
        if not reason:
            raise exceptions.ValidationError("Se requiere un motivo para invalidar la sesión.")
        try:
            invalidate_work_session(session=session, actor=request.user, reason=reason)
        except DjangoValidationError as exc:
            raise exceptions.ValidationError(exc.messages)
        return response.Response(WorkSessionSerializer(session).data, status=status.HTTP_200_OK)
