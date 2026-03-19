from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class AIUsage(models.Model):
    class ServiceType(models.TextChoices):
        TRANSCRIPTION = "transcription", _("Transcription")
        EXTRACTION = "extraction", _("Extraction")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="ai_usage",
    )
    record = models.ForeignKey(
        "records.Record",
        on_delete=models.CASCADE,
        related_name="ai_usage",
    )
    provider = models.CharField(max_length=50)
    service_type = models.CharField(max_length=50, choices=ServiceType.choices)
    duration_seconds = models.FloatField(default=0)
    tokens_used = models.IntegerField(default=0)
    cost_usd = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "created_at"],
                name="usage_org_created_idx",
            ),
            models.Index(
                fields=["record", "service_type"],
                name="usage_record_service_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name} {self.service_type} {self.provider}"
