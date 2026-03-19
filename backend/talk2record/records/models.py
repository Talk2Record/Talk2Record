from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _


class Record(models.Model):
    class Source(models.TextChoices):
        WHATSAPP = "whatsapp", _("WhatsApp")
        UPLOAD = "upload", _("Upload")
        API = "api", _("API")

    class Status(models.TextChoices):
        RECEIVED = "received", _("Received")
        TRANSCRIBED = "transcribed", _("Transcribed")
        REVIEW = "review", _("Review")
        STORED = "stored", _("Stored")
        FAILED = "failed", _("Failed")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="records",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_records",
    )
    source = models.CharField(max_length=32, choices=Source.choices, default=Source.WHATSAPP)
    source_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RECEIVED)
    customer_name = models.CharField(max_length=255)
    product = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    payment_method = models.CharField(max_length=64, blank=True)
    voice_transcript = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    audio_url = models.URLField(blank=True)
    processing_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_reference"],
                condition=~Q(source_reference=""),
                name="unique_record_source_reference_per_source",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.customer_name}"
