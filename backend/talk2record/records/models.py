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
        TRANSCRIBING = "transcribing", _("Transcribing")
        TRANSCRIBED = "transcribed", _("Transcribed")
        EXTRACTING = "extracting", _("Extracting")
        EXTRACTED = "extracted", _("Extracted")
        REVIEW = "review", _("Review")
        STORED = "stored", _("Stored")
        FAILED = "failed", _("Failed")
        DEAD_LETTER = "dead_letter", _("Dead letter")

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
    source = models.CharField(
        max_length=32,
        choices=Source.choices,
        default=Source.WHATSAPP,
    )
    source_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    customer_name = models.CharField(max_length=255)
    product = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="USD")
    payment_method = models.CharField(max_length=64, blank=True)
    voice_transcript = models.TextField(blank=True)
    confidence_score = models.DecimalField(max_digits=4, decimal_places=3, default=0)
    ai_transcription_provider = models.CharField(max_length=64, blank=True)
    ai_extraction_provider = models.CharField(max_length=64, blank=True)
    ai_prompt_version = models.CharField(max_length=32, blank=True)
    audio_url = models.URLField(blank=True)
    processing_error = models.TextField(blank=True)
    processing_error_step = models.CharField(max_length=32, blank=True)
    processing_retry_count = models.PositiveSmallIntegerField(default=0)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    dead_lettered_at = models.DateTimeField(null=True, blank=True)
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
        indexes = [
            models.Index(
                fields=["organization", "created_at"],
                name="record_org_created_idx",
            ),
            models.Index(
                fields=["status", "updated_at"],
                name="record_status_updated_idx",
            ),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.organization.name}: {self.customer_name}"


class RecordProcessingState(models.Model):
    record = models.ForeignKey(
        Record,
        on_delete=models.CASCADE,
        related_name="processing_states",
    )
    status = models.CharField(max_length=32, choices=Record.Status.choices)
    details = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(
                fields=["record", "updated_at"],
                name="record_state_timeline_idx",
            ),
            models.Index(
                fields=["status", "updated_at"],
                name="record_state_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.record_id}:{self.status}"
