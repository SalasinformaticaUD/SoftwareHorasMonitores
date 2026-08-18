from apps.annotations.selectors import visible_annotations_for_user
from apps.monitors.models import AcademicSemester
from tests.factories import AnnotationFactory, MonitorFactory, UserFactory


def test_visible_annotations_include_only_current_semester_monitors(db):
    leader = UserFactory()
    old_semester = AcademicSemester.objects.create(name="2025-3", is_active=False)
    old_monitor = MonitorFactory(
        semester=old_semester,
        full_name="MARIA GOMEZ",
        codigo_estudiante="202200002",
        department=leader.department,
        is_active=True,
    )
    current_monitor = MonitorFactory(
        full_name="Maria Gomez",
        codigo_estudiante="202600002",
        department=leader.department,
    )
    old_annotation = AnnotationFactory(monitor=old_monitor, leader=leader)
    current_annotation = AnnotationFactory(monitor=current_monitor, leader=leader)

    annotations = visible_annotations_for_user(leader)

    assert current_annotation in annotations
    assert old_annotation not in annotations
