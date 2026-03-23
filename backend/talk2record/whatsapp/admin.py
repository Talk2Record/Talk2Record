from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from talk2record.whatsapp.credentials_admin import save_whatsapp_api_credential
from talk2record.whatsapp.forms import WhatsAppSettingsAdminForm
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppSettings


@admin.register(WhatsAppSettings)
class WhatsAppSettingsAdmin(ModelAdmin):
    form = WhatsAppSettingsAdminForm
    list_display = ["__str__", "enabled", "updated_at", "created_at"]
    ordering = ("pk",)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(pk=1)

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        if isinstance(form, WhatsAppSettingsAdminForm):
            save_whatsapp_api_credential(
                obj,
                access_token=form.cleaned_data.get("access_token") or "",
                app_secret=form.cleaned_data.get("app_secret") or "",
            )

    def get_fieldsets(self, request, obj=None):
        return (
            (None, {"fields": ("enabled",)}),
            (
                _("Identifiers & webhook"),
                {
                    "fields": (
                        "graph_api_version",
                        "phone_number_id",
                        "waba_id",
                        "business_id",
                        "verify_token",
                    ),
                },
            ),
            (
                _("Secrets (encrypted at rest)"),
                {
                    "fields": ("access_token", "app_secret"),
                    "description": _(
                        "Leave password fields empty to keep the current values. "
                        "Both are stored in the encrypted credential field."
                    ),
                },
            ),
        )


@admin.register(WhatsAppInboundRoute)
class WhatsAppInboundRouteAdmin(ModelAdmin):
    """Maps Meta ``phone_number_id`` values to organizations for webhook routing."""

    list_display = [
        "phone_number_id",
        "organization",
        "updated_at",
        "created_at",
    ]
    list_select_related = ("organization",)
    search_fields = [
        "phone_number_id",
        "organization__name",
        "organization__slug",
    ]
    ordering = ("phone_number_id",)
    fieldsets = (
        (
            None,
            {
                "fields": ("phone_number_id", "organization"),
                "description": _(
                    "Use the Phone Number ID from WhatsApp Manager or the Graph API."
                ),
            },
        ),
    )
