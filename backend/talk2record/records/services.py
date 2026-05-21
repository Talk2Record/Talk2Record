from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import RECORD_STORED
from talk2record.records.models import Record, RecordArtifact

if TYPE_CHECKING:
    from talk2record.ai.providers.base import ExtractionResult, TranscriptionResult
    from talk2record.taxonomy.services.orchestrator import PipelineOutcome


def _json_safe(value: object) -> object:
    """Recursively convert Decimal values to strings for safe JSONField storage."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value


class RecordProcessingService:
    """
    Domain service for Record lifecycle operations.

    Handles persisting AI outputs as RecordArtifacts and managing the
    final STORED transition.  Retry logic and state machine orchestration
    live in ingestion.tasks.ProcessingStepRunner.
    """

    @staticmethod
    def save_transcript_artifact(record: Record, result: TranscriptionResult) -> RecordArtifact:
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="transcript",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.TEXT,
                "content": {"text": result.transcript},
                "provider": result.provider,
                "model": result.model,
            },
        )
        return artifact

    @staticmethod
    def save_extraction_artifact(record: Record, result: ExtractionResult) -> RecordArtifact:
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="extraction",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.JSON,
                "content": _json_safe(result.data),
                "provider": result.provider,
                "model": result.model,
                "prompt_version": result.prompt_version,
            },
        )
        return artifact

    # ------------------------------------------------------------------
    # Dynamic taxonomy pipeline persistence
    # ------------------------------------------------------------------

    @staticmethod
    def save_classification_artifact(record: Record, outcome: PipelineOutcome) -> RecordArtifact:
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="classification",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.JSON,
                "content": _json_safe(
                    {
                        "industries": outcome.detected_industries,
                        "categories": outcome.detected_categories,
                        "source": outcome.classification.source,
                        "raw_llm_response": outcome.classification.raw_llm_response,
                    },
                ),
            },
        )
        return artifact

    @staticmethod
    def save_normalization_artifact(record: Record, outcome: PipelineOutcome) -> RecordArtifact:
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="normalization",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.JSON,
                "content": _json_safe(
                    {
                        "text": outcome.normalization.text,
                        "applied": outcome.normalization.applied,
                    },
                ),
            },
        )
        return artifact

    @staticmethod
    def save_dynamic_extraction_artifact(
        record: Record,
        outcome: PipelineOutcome,
    ) -> RecordArtifact:
        if outcome.extractions:
            primary = outcome.extractions[0].extraction
            provider = primary.provider
            model = primary.model
            prompt_version = primary.prompt_version
            schema_version = primary.schema_version
        else:
            provider = ""
            model = ""
            prompt_version = ""
            schema_version = ""

        content = {
            "categories": [extraction.to_artifact() for extraction in outcome.extractions],
            "primary": outcome.extracted_data,
        }
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="extraction",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.JSON,
                "content": _json_safe(content),
                "provider": provider,
                "model": model,
                "prompt_version": prompt_version,
                "schema_version": schema_version,
            },
        )
        return artifact

    @staticmethod
    def save_validation_artifact(record: Record, outcome: PipelineOutcome) -> RecordArtifact:
        artifact, _ = RecordArtifact.objects.update_or_create(
            record=record,
            key="validation",
            defaults={
                "artifact_type": RecordArtifact.ArtifactType.JSON,
                "content": _json_safe(
                    {
                        "errors": outcome.validation_errors,
                        "needs_review": outcome.needs_review,
                        "confidence_score": outcome.confidence_score,
                    },
                ),
            },
        )
        return artifact

    @staticmethod
    def apply_pipeline_outcome(record: Record, outcome: PipelineOutcome) -> None:
        """Update the projection columns on ``Record`` from the pipeline outcome."""

        record.detected_industries = _json_safe(outcome.detected_industries)
        record.detected_categories = _json_safe(outcome.detected_categories)
        record.extracted_data = _json_safe(outcome.extracted_data)
        record.validation_errors = _json_safe(outcome.validation_errors)
        record.confidence_score = Decimal(str(round(outcome.confidence_score, 4)))
        record.save(
            update_fields=[
                "detected_industries",
                "detected_categories",
                "extracted_data",
                "validation_errors",
                "confidence_score",
                "updated_at",
            ],
        )

    @staticmethod
    def get_transcript(record: Record) -> str:
        artifact = record.get_artifact("transcript")
        if artifact is None:
            return ""
        return str(artifact.content.get("text", ""))

    @staticmethod
    def store(record: Record) -> Record:
        record.status = Record.Status.STORED
        record.save(update_fields=["status", "updated_at"])

        metadata = RecordProcessingService._build_stored_metadata(record)
        publish_after_commit(
            DomainEvent(
                name=RECORD_STORED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "source": record.source,
                    "status": record.status,
                    **metadata,
                },
            ),
        )
        return record

    @staticmethod
    def _build_stored_metadata(record: Record) -> dict:
        """Compose the notification title + summary for a stored record."""

        title, message = RecordProcessingService._dynamic_summary(record)
        if title is None:
            title = "Voice note has been processed"
            message = f"Record {record.source_reference or record.pk} is ready."
        return {"title": title, "message": message, "link_url": "/dashboard/records"}

    @staticmethod
    def _dynamic_summary(record: Record) -> tuple[str | None, str]:
        categories = record.detected_categories or []
        data = record.extracted_data
        if not categories and not data:
            return None, ""
        category_label = ""
        if categories:
            first = categories[0]
            category_label = f"{first.get('industry', '')}.{first.get('slug', '')}".strip(".")

        title = (
            f"Voice note classified as {category_label}"
            if category_label
            else "Voice note has been processed"
        )

        summary_bits: list[str] = []
        if isinstance(data, dict):
            for key, value in list(data.items())[:3]:
                if value in (None, "", [], {}):
                    continue
                summary_bits.append(f"{key}: {value}")
        message = ", ".join(summary_bits) or f"Record {record.source_reference or record.pk} is ready."
        return title, message
