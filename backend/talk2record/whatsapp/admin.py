from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin

from talk2record.integrations.models import WhatsAppInboundRoute


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
                    "Use the Phone Number ID from WhatsApp Manager / Graph API "
                    "(Postman variable Phone-Number-ID)."
                ),
            },
        ),
    )
