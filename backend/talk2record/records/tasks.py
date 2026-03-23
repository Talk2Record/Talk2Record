from __future__ import annotations

from celery import shared_task

from talk2record.ai.services.extraction import ExtractionService
from talk2record.ai.services.transcription import TranscriptionService
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.records.models import Record
from talk2record.records.services import RecordProcessingService


def _notify_record_failed(record: Record, error: str) -> None:
    if record.created_by_id:
        NotificationService.create(
            user=record.created_by,
            notification_type=Notification.Type.RECORD_FAILED,
            title="Voice note processing failed",
            message=error or "An error occurred while processing your voice note.",
            organization=record.organization,
            metadata={"record_id": record.pk},
        )


@shared_task
def transcribe_voice(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    try:
        result = TranscriptionService.transcribe(record)
        RecordProcessingService.save_transcript_artifact(record, result)
        record.status = Record.Status.TRANSCRIBED
        record.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        record.status = Record.Status.FAILED
        record.processing_error = str(exc)
        record.save(update_fields=["status", "processing_error", "updated_at"])
        _notify_record_failed(record, str(exc))
        raise


@shared_task
def extract_structured_data(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    try:
        transcript = RecordProcessingService.get_transcript(record)
        result = ExtractionService.extract(transcript=transcript)
        RecordProcessingService.save_extraction_artifact(record, result)
        record.status = Record.Status.EXTRACTED
        record.save(update_fields=["status", "updated_at"])
    except Exception as exc:
        record.status = Record.Status.FAILED
        record.processing_error = str(exc)
        record.save(update_fields=["status", "processing_error", "updated_at"])
        _notify_record_failed(record, str(exc))
        raise


@shared_task
def store_record(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    try:
        RecordProcessingService.store(record)
    except Exception as exc:
        record.status = Record.Status.FAILED
        record.processing_error = str(exc)
        record.save(update_fields=["status", "processing_error", "updated_at"])
        _notify_record_failed(record, str(exc))
        raise
