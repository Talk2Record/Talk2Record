from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Membership
from .models import MembershipInvitation
from .models import Organization
from .models import OrganizationAPIKey


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = ["name", "slug", "status", "default_currency", "created_at"]
    search_fields = ["name", "slug"]
    list_filter = ["status", "default_currency"]
    ordering = ("name",)


@admin.register(Membership)
class MembershipAdmin(ModelAdmin):
    list_display = ["user", "organization", "role", "status", "joined_at"]
    list_select_related = ("user", "organization")
    search_fields = ["user__email", "organization__name"]
    list_filter = ["role", "status"]


@admin.register(MembershipInvitation)
class MembershipInvitationAdmin(ModelAdmin):
    list_display = [
        "email",
        "organization",
        "role",
        "status",
        "invited_by",
        "expires_at",
        "accepted_at",
        "created_at",
    ]
    list_select_related = ("organization", "invited_by", "accepted_by")
    search_fields = ["email", "organization__name", "organization__slug"]
    list_filter = ["status", "role", "created_at"]
    readonly_fields = ["token_hash", "created_at", "updated_at", "accepted_at", "revoked_at"]


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
    list_select_related = ("organization",)
    search_fields = ["name", "organization__name", "key_prefix"]
    list_filter = ["is_active", "created_at", "expires_at"]
