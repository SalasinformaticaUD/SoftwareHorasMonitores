from apps.annotations.forms import AnnotationAdjustmentForm
from apps.common.choices import AnnotationActionChoices, AnnotationTypeChoices
from apps.monitors.models import AcademicSemester
from tests.factories import MonitorFactory, UserFactory


def test_annotation_adjustment_form_converts_added_hours_to_minutes(db):
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    form = AnnotationAdjustmentForm(
        actor=leader,
        data={
            "monitor": str(monitor.id),
            "annotation_type": AnnotationTypeChoices.VIRTUAL_HOURS,
            "action": AnnotationActionChoices.ADD,
            "hours": "2",
            "occurred_on": "2026-04-16",
            "description": "Horas virtuales aprobadas.",
        },
    )

    assert form.is_valid()
    assert form.cleaned_data["delta_minutes"] == 120


def test_annotation_adjustment_form_converts_deducted_hours_to_negative_minutes(db):
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    form = AnnotationAdjustmentForm(
        actor=leader,
        data={
            "monitor": str(monitor.id),
            "annotation_type": AnnotationTypeChoices.NOVELTY,
            "action": AnnotationActionChoices.DEDUCT,
            "hours": "2",
            "occurred_on": "2026-04-16",
            "description": "Corrección manual de horas aprobadas por accidente.",
        },
    )

    assert form.is_valid()
    assert form.cleaned_data["delta_minutes"] == -120


def test_annotation_adjustment_form_rejects_more_than_24_hours(db):
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    form = AnnotationAdjustmentForm(
        actor=leader,
        data={
            "monitor": str(monitor.id),
            "annotation_type": AnnotationTypeChoices.VIRTUAL_HOURS,
            "action": AnnotationActionChoices.ADD,
            "hours": "50",
            "occurred_on": "2026-04-16",
            "description": "Carga imposible.",
        },
    )

    assert form.is_valid() is False
    assert "hours" in form.errors


def test_annotation_adjustment_form_lists_only_current_semester_monitors(db):
    leader = UserFactory()
    old_semester = AcademicSemester.objects.create(name="2025-3", is_active=False)
    old_monitor = MonitorFactory(
        semester=old_semester,
        full_name="JOSE ALVAREZ",
        codigo_estudiante="202200001",
        department=leader.department,
        is_active=True,
    )
    current_monitor = MonitorFactory(
        full_name="Jose Alvarez",
        codigo_estudiante="202600001",
        department=leader.department,
    )

    form = AnnotationAdjustmentForm(actor=leader)

    assert current_monitor in form.fields["monitor"].queryset
    assert old_monitor not in form.fields["monitor"].queryset
