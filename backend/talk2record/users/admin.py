from contextlib import suppress

from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
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
