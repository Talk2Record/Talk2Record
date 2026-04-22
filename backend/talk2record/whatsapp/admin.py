from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from talk2record.whatsapp.credentials_admin import save_whatsapp_api_credential
from talk2record.whatsapp.forms import WhatsAppSettingsAdminForm
from talk2record.whatsapp.models import WhatsAppAccount
from talk2record.whatsapp.models import WhatsAppConversation
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppMessage
from talk2record.whatsapp.models import WhatsAppSettings
from talk2record.whatsapp.models import WhatsAppTemplate


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


@admin.register(WhatsAppAccount)
class WhatsAppAccountAdmin(ModelAdmin):
    list_display = [
        "phone_number_id",
        "display_number",
        "organization",
        "status",
        "verified_at",
        "created_at",
    ]
    list_select_related = ("organization",)
    list_filter = ("status",)
    search_fields = [
        "phone_number_id",
        "display_number",
        "organization__name",
        "organization__slug",
    ]
    ordering = ("phone_number_id",)


@admin.register(WhatsAppConversation)
class WhatsAppConversationAdmin(ModelAdmin):
    list_display = [
        "contact_wa_id",
        "contact_name",
        "account",
        "organization",
        "last_message_at",
    ]
    list_select_related = ("account", "organization")
    search_fields = [
        "contact_wa_id",
        "contact_name",
        "account__phone_number_id",
        "organization__name",
    ]
    readonly_fields = [
        "account",
        "organization",
        "contact_wa_id",
        "last_message_at",
        "last_inbound_at",
        "last_outbound_at",
        "created_at",
        "updated_at",
    ]
    ordering = ("-last_message_at",)


@admin.register(WhatsAppMessage)
class WhatsAppMessageAdmin(ModelAdmin):
    list_display = [
        "wa_message_id",
        "direction",
        "message_type",
        "status",
        "organization",
        "created_at",
    ]
    list_select_related = ("organization", "conversation")
    list_filter = ("direction", "message_type", "status")
    search_fields = [
        "wa_message_id",
        "body",
        "conversation__contact_wa_id",
        "organization__name",
    ]
    readonly_fields = [
        "conversation",
        "organization",
        "wa_message_id",
        "direction",
        "message_type",
        "status",
        "body",
        "media_id",
        "media_url",
        "media_mime",
        "media_sha256",
        "raw_payload",
        "error_code",
        "error_message",
        "timestamp",
        "created_at",
        "updated_at",
    ]
    ordering = ("-created_at",)


@admin.register(WhatsAppTemplate)
class WhatsAppTemplateAdmin(ModelAdmin):
    list_display = [
        "name",
        "language",
        "category",
        "status",
        "organization",
        "updated_at",
    ]
    list_select_related = ("organization",)
    list_filter = ("category", "status")
    search_fields = ["name", "language", "organization__name", "provider_id"]
    ordering = ("name", "language")
