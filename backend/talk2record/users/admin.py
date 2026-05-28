from contextlib import suppress

from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User
from .models import UserSession

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]

with suppress(admin.sites.NotRegistered):
    admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(ModelAdmin, auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "name",
                    "timezone",
                    "locale",
                    "avatar_url",
                    "current_organization",
                    "onboarding_completed",
                    "latest_required_legal_acceptance_at",
                    "mfa_enabled",
                ),
            },
        ),
        (
            _("Suspension"),
            {
                "fields": ("suspended_at", "suspended_reason"),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = [
        "email",
        "name",
        "current_organization",
        "onboarding_completed",
        "is_active",
        "suspended_at",
        "is_superuser",
    ]
    list_filter = ["is_active", "is_staff", "is_superuser", "onboarding_completed"]
    search_fields = ["email", "name"]
    ordering = ["id"]
    actions = ["reset_billing_primary_org"]

    @admin.action(description=_("Reset billing for the user's primary organisation"))
    def reset_billing_primary_org(self, request, queryset):
        """Resolve each user's primary organisation, then reset billing.

        "Primary" = ``user.current_organization``, falling back to the first
        active membership. Users without any org are skipped with a warning.
        Confirmation is collected on a second POST so admins must supply a
        reason (required for the audit trail).
        """
        from talk2record.billing.admin import _render_reset_confirmation
        from talk2record.billing.admin import _run_billing_reset
        from talk2record.organizations.models import Membership

        organizations = []
        seen = set()
        for user in queryset:
            org = user.current_organization
            if org is None:
                membership = (
                    Membership.objects.filter(
                        user=user,
                        status=Membership.Status.ACTIVE,
                    )
                    .select_related("organization")
                    .first()
                )
                org = membership.organization if membership else None
            if org is None:
                messages.warning(
                    request,
                    f"{user.email}: no organisation to reset.",
                )
                continue
            if org.pk in seen:
                continue
            seen.add(org.pk)
            organizations.append(org)

        if not organizations:
            messages.error(
                request,
                _("None of the selected users have an organisation to reset."),
            )
            return None

        if request.POST.get("confirm") == "1":
            reason = (request.POST.get("reason") or "").strip()
            also_reset_onboarding = request.POST.get("also_reset_onboarding") == "on"
            if not reason:
                messages.error(request, _("A reason is required to reset billing."))
                return _render_reset_confirmation(
                    request,
                    organizations,
                    back_url=reverse("admin:users_user_changelist"),
                    title=_("Reset billing — confirm"),
                )
            _run_billing_reset(
                request,
                organizations,
                reason,
                also_reset_onboarding=also_reset_onboarding,
            )
            return None
        return _render_reset_confirmation(
            request,
            organizations,
            back_url=reverse("admin:users_user_changelist"),
            title=_("Reset billing — confirm"),
        )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Group)
class GroupAdmin(ModelAdmin, BaseGroupAdmin):
    pass


@admin.register(UserSession)
class UserSessionAdmin(ModelAdmin):
    list_display = [
        "user",
        "ip_address",
        "user_agent",
        "created_at",
        "revoked_at",
        "expires_at",
    ]
    list_select_related = ("user",)
    list_filter = ["revoked_at", "expires_at"]
    search_fields = ["user__email", "ip_address"]
    readonly_fields = [
        "user",
        "refresh_jti",
        "ip_address",
        "user_agent",
        "created_at",
        "last_seen_at",
        "revoked_at",
        "expires_at",
    ]
