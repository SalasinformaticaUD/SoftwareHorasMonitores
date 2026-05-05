from apps.annotations.services import create_annotation
from apps.reports.selectors import aggregate_monitor_metrics
from tests.factories import MonitorFactory, UserFactory, WorkSessionFactory


def test_annotations_affect_monitor_totals_and_remaining_hours(db):
    leader = UserFactory()
    monitor = MonitorFactory(department=leader.department)
    WorkSessionFactory(
        monitor=monitor,
        raw_record__monitor=monitor,
        normal_minutes=240,
        overtime_minutes=60,
        overtime_status="approved",
        penalty_minutes=120,
    )
    create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="virtual_hours",
        description="Se agregan horas virtuales.",
        action="add",
        delta_minutes=120,
        occurred_on="2026-04-16",
    )
    create_annotation(
        leader=leader,
        monitor=monitor,
        annotation_type="novelty",
        description="Corrección manual por error.",
        action="deduct",
        delta_minutes=-60,
        occurred_on="2026-04-16",
    )

    metrics = aggregate_monitor_metrics(monitor=monitor)

    assert metrics["annotation_delta_minutes"] == 60
    assert metrics["penalty_minutes"] == 120
    assert metrics["net_total_minutes"] == 360
    assert metrics["remaining_minutes"] == (192 * 60) - 360
