import pytest
from django.core.exceptions import ValidationError

from apps.annotations.services import create_annotation, delete_annotation, update_annotation
from tests.factories import MonitorFactory, UserFactory


@pytest.mark.django_db
def test_annotation_can_add_or_deduct_minutes():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)

    plus = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="virtual_hours",
        description="Se ajusta una sesión virtual.",
        action="add",
        delta_minutes=45,
        occurred_on="2026-04-13",
    )
    minus = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="permission",
        description="Descuento por permiso.",
        action="deduct",
        delta_minutes=-30,
        occurred_on="2026-04-13",
    )

    assert plus.delta_minutes == 45
    assert minus.delta_minutes == -30


@pytest.mark.django_db
def test_annotation_can_be_updated():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    other_monitor = MonitorFactory(department=leader.department)
    annotation = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="virtual_hours",
        description="Registro inicial.",
        action="add",
        delta_minutes=60,
        occurred_on="2026-04-13",
    )

    updated = update_annotation(
        actor=leader,
        annotation=annotation,
        monitor=other_monitor,
        annotation_type="novelty",
        description="Corrección manual.",
        action="deduct",
        delta_minutes=-120,
        occurred_on="2026-04-14",
    )

    assert updated.monitor == other_monitor
    assert updated.annotation_type == "novelty"
    assert updated.description == "Corrección manual."
    assert updated.action == "deduct"
    assert updated.delta_minutes == -120


@pytest.mark.django_db
def test_annotation_can_be_deleted():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    annotation = create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="virtual_hours",
        description="Registro temporal.",
        action="add",
        delta_minutes=60,
        occurred_on="2026-04-13",
    )

    delete_annotation(actor=leader, annotation=annotation)

    from apps.annotations.models import Annotation

    assert Annotation.objects.filter(pk=annotation.pk).exists() is False


@pytest.mark.django_db
def test_annotation_rejects_more_than_24_hours_even_outside_form():
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)

    with pytest.raises(ValidationError):
        create_annotation(
            leader=leader,
            monitor=monitor,
            annotation_type="virtual_hours",
            description="Carga imposible.",
            action="add",
            delta_minutes=3000,
            occurred_on="2026-04-13",
        )
