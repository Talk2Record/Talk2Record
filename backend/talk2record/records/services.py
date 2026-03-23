from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import RECORD_STORED
from talk2record.records.models import Record, RecordArtifact

if TYPE_CHECKING:
    from talk2record.ai.providers.base import ExtractionResult, TranscriptionResult


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
        extraction = record.get_artifact("extraction")
        if extraction is not None:
            data = extraction.content
            title = f"Voice note from {data.get('customer_name', 'Unknown')} has been processed"
            message = (
                f"Record: {data.get('product', '-')} - "
                f"{data.get('quantity', 1)} x "
                f"{data.get('currency', 'USD')} {data.get('amount', '0.00')}"
            )
        else:
            title = "Voice note has been processed"
            message = f"Record {record.source_reference or record.pk} is ready."
        return {"title": title, "message": message, "link_url": "/dashboard/records"}
