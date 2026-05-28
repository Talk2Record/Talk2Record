from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .models import Membership
from .models import MembershipInvitation
from .models import Organization
from .models import OrganizationAPIKey


@admin.register(Organization)
class OrganizationAdmin(ModelAdmin):
    list_display = [
        "name",
        "slug",
        "status",
        "default_currency",
        "billing_state_version",
        "billing_review_link",
        "created_at",
    ]
    search_fields = ["name", "slug"]
    list_filter = ["status", "default_currency"]
    ordering = ("name",)
    actions = ["reset_billing"]

    @admin.display(description=_("Billing review"))
    def billing_review_link(self, obj):
        """Deep-link to the per-org Billing Recovery page (Phase 5)."""
        url = reverse("admin_billing_organization_review", args=[obj.pk])
        return format_html(
            '<a href="{}" class="text-primary-600 hover:underline">{}</a>',
            url,
            _("Open"),
        )

    @admin.action(description=_("Reset billing for selected organisations"))
    def reset_billing(self, request, queryset):
        """Two-step billing reset action.

        Delegates to :func:`talk2record.billing.admin._run_billing_reset` so
        the confirmation flow + per-org error handling is identical to the
        Subscription / User admin actions.
        """
        # Local import: keeps the organizations app independent of billing
        # at module import time (billing depends on organizations, not
        # the other way around).
        from talk2record.billing.admin import _render_reset_confirmation
        from talk2record.billing.admin import _run_billing_reset

        if request.POST.get("confirm") == "1":
            reason = (request.POST.get("reason") or "").strip()
            also_reset_onboarding = request.POST.get("also_reset_onboarding") == "on"
            if not reason:
                messages.error(request, _("A reason is required to reset billing."))
                return _render_reset_confirmation(
                    request,
                    queryset,
                    back_url=reverse("admin:organizations_organization_changelist"),
                    title=_("Reset billing — confirm"),
                )
            _run_billing_reset(
                request,
                queryset,
                reason,
                also_reset_onboarding=also_reset_onboarding,
            )
            return None
        return _render_reset_confirmation(
            request,
            queryset,
            back_url=reverse("admin:organizations_organization_changelist"),
            title=_("Reset billing — confirm"),
        )


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
    readonly_fields = [
        "token_hash",
        "created_at",
        "updated_at",
        "accepted_at",
        "revoked_at",
    ]


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
