from django.contrib import admin

from .models import Membership
from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "status", "default_currency", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["status", "default_currency"]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "organization", "role", "status", "joined_at"]
    search_fields = ["user__email", "organization__name"]
    list_filter = ["role", "status"]
