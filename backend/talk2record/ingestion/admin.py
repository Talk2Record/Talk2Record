from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.paginator import InfinitePaginator

from talk2record.ingestion.models import WhatsAppRawPayload


@admin.register(WhatsAppRawPayload)
class WhatsAppRawPayloadAdmin(ModelAdmin):
    list_display = [
        "message_id",
        "organization",
        "processed",
        "received_at",
        "processed_at",
    ]
    list_select_related = ("organization",)
    list_filter = ["processed", "received_at"]
    search_fields = ["message_id", "organization__name", "media_id"]
    ordering = ("-received_at",)
    readonly_fields = ["received_at"]
    paginator = InfinitePaginator
    show_full_result_count = False
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "organization",
                    "message_id",
                    "processed",
                    "processed_at",
                    "received_at",
                ),
            },
        ),
        (_("Payload & media"), {"fields": ("payload", "media_id", "media_url")}),
    )
