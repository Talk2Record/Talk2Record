from __future__ import annotations

from django.db import models


class WhatsAppRawPayload(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="whatsapp_raw_payloads",
    )
    message_id = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    media_url = models.URLField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["organization", "received_at"],
                name="wa_raw_org_received_idx",
            ),
            models.Index(
                fields=["processed", "received_at"],
                name="wa_raw_processed_idx",
            ),
        ]
        ordering = ["-received_at"]

    def __str__(self) -> str:
        return f"{self.organization.name} - {self.message_id}"
