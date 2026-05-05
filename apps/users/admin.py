from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.users.models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "role", "department", "is_active", "is_staff")
    list_filter = ("role", "department", "is_active", "is_staff")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Dominio", {"fields": ("role", "department")}),
    )

