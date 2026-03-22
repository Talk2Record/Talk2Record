from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Membership
from .models import Organization
from .models import OrganizationAPIKey


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ["name", "slug", "status", "default_currency", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["status", "default_currency"]


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    list_display = ["user", "organization", "role", "status", "joined_at"]
    search_fields = ["user__email", "organization__name"]
    list_filter = ["role", "status"]


@admin.register(OrganizationAPIKey)
class OrganizationAPIKeyAdmin(ModelAdmin):
    list_display = [
        "name",
        "organization",
        "is_active",
        "rate_limit_per_minute",
        "expires_at",
        "revoked_at",
        "last_used_at",
        "created_at",
    ]
    search_fields = ["name", "organization__name", "key_prefix"]
    list_filter = ["is_active", "created_at", "expires_at"]
