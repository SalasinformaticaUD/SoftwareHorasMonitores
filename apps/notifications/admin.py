from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("title", "event_type", "department", "recipient", "is_read", "created_at")
    list_filter = ("event_type", "department", "is_read")
    search_fields = ("title", "body")

