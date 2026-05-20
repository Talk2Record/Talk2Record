from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Record(models.Model):
    class Source(models.TextChoices):
        WHATSAPP = "whatsapp", _("WhatsApp")
        UPLOAD = "upload", _("Upload")
        API = "api", _("API")

    class Type(models.TextChoices):
        VOICE_NOTE = "voice_note", _("Voice Note")
        CALL = "call", _("Call")
        MEETING = "meeting", _("Meeting")
        DOCUMENT = "document", _("Document")

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
    type = models.CharField(
        max_length=32,
        choices=Type.choices,
        default=Type.VOICE_NOTE,
    )
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.RECEIVED,
    )
    audio_url = models.URLField(blank=True)
    media_id = models.CharField(max_length=255, blank=True)
    # --- Dynamic extraction outputs (current best view; immutable history
    # is kept on RecordArtifact rows for replay + audit). ---
    detected_industries = models.JSONField(default=list, blank=True)
    detected_categories = models.JSONField(default=list, blank=True)
    extracted_data = models.JSONField(default=dict, blank=True)
    validation_errors = models.JSONField(default=list, blank=True)
    confidence_score = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0,
    )
    processing_step = models.CharField(max_length=64, blank=True)
    # --- Error tracking ---
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
                condition=~models.Q(source_reference=""),
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
        return f"{self.organization.name}: {self.source_reference or self.pk}"

    def get_artifact(self, key: str) -> RecordArtifact | None:
        return self.artifacts.filter(key=key).first()


class RecordArtifact(models.Model):
    class ArtifactType(models.TextChoices):
        TEXT = "text", _("Text")
        JSON = "json", _("JSON")
        NUMBER = "number", _("Number")
        FILE = "file", _("File")

    record = models.ForeignKey(
        Record,
        on_delete=models.CASCADE,
        related_name="artifacts",
    )
    key = models.CharField(max_length=100)
    artifact_type = models.CharField(
        max_length=50,
        choices=ArtifactType.choices,
        default=ArtifactType.TEXT,
    )
    content = models.JSONField()
    provider = models.CharField(max_length=64, blank=True)
    model = models.CharField(max_length=64, blank=True)
    prompt_version = models.CharField(max_length=32, blank=True)
    schema_version = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("record", "key")]
        indexes = [
            models.Index(
                fields=["record", "key"],
                name="artifact_record_key_idx",
            ),
            models.Index(
                fields=["key", "created_at"],
                name="artifact_key_created_idx",
            ),
        ]
        ordering = ["key", "-created_at"]

    def __str__(self) -> str:
        return f"{self.record_id}:{self.key}"


class RecordSchema(models.Model):
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=20)
    definition = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("name", "version")]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name}@{self.version}"


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
