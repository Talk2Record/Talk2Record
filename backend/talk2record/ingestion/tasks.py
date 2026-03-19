from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.records.models import Record
from talk2record.records.services import RecordProcessingService


@shared_task
def process_whatsapp_record(record_id: int, payload_id: int | None = None) -> None:
    record = Record.objects.get(pk=record_id)
    try:
        RecordProcessingService.transcribe(record)
        RecordProcessingService.extract_structured_data(record)
        RecordProcessingService.store(record)
        if payload_id is not None:
            WhatsAppRawPayload.objects.filter(pk=payload_id).update(
                processed=True,
                processed_at=timezone.now(),
            )
    except Exception as exc:
        record.status = Record.Status.FAILED
        record.processing_error = str(exc)
        record.save(update_fields=["status", "processing_error", "updated_at"])
        raise
