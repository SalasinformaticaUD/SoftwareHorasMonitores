from django.db.models import QuerySet

from apps.annotations.models import Annotation
from apps.common.choices import UserRoleChoices


def visible_annotations_for_user(user) -> QuerySet[Annotation]:
    queryset = Annotation.objects.select_related("leader", "monitor", "session")
    if user.role == UserRoleChoices.ADMIN:
        return queryset
    return queryset.filter(department=user.department)

