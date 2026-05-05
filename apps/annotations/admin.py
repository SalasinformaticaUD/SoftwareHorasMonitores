from django.contrib import admin

from apps.annotations.models import Annotation


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ("monitor", "annotation_type", "action", "delta_minutes", "occurred_on", "leader")
    list_filter = ("annotation_type", "action", "department")
    search_fields = ("monitor__full_name", "description")

