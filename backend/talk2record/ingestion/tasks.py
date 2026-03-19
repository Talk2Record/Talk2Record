from __future__ import annotations

from time import monotonic

from celery import shared_task
from django.utils import timezone

from talk2record.ai.services.extraction import ExtractionService
from talk2record.ai.services.transcription import TranscriptionService
from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.records.models import Record
from talk2record.records.models import RecordProcessingState
from talk2record.records.services import RecordProcessingService
from talk2record.usage.models import AIUsage
from talk2record.usage.services import UsageTrackingService

MAX_STEP_RETRIES = 3


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


def _append_processing_state(
    record: Record,
    status: str,
    details: dict | None = None,
) -> None:
    RecordProcessingState.objects.create(
        record=record,
        status=status,
        details=details or {},
    )


def _run_step(*, record: Record, step: str) -> None:
    if step == "transcribe":
        record.status = Record.Status.TRANSCRIBING
        record.save(update_fields=["status", "updated_at"])
        _append_processing_state(record, Record.Status.TRANSCRIBING)
        started = monotonic()
        result = TranscriptionService.transcribe(record)
        record.voice_transcript = result.transcript
        record.ai_transcription_provider = result.provider
        record.status = Record.Status.TRANSCRIBED
        record.save(
            update_fields=[
                "voice_transcript",
                "ai_transcription_provider",
                "status",
                "updated_at",
            ],
        )
        duration = monotonic() - started
        UsageTrackingService.log_ai_usage(
            record=record,
            provider=result.provider,
            service_type=AIUsage.ServiceType.TRANSCRIPTION,
            duration_seconds=duration,
        )
        _append_processing_state(
            record,
            Record.Status.TRANSCRIBED,
            {
                "provider": result.provider,
                "model": result.model,
                "duration_seconds": duration,
            },
        )
        return

    if step == "extract":
        record.status = Record.Status.EXTRACTING
        record.save(update_fields=["status", "updated_at"])
        _append_processing_state(record, Record.Status.EXTRACTING)
        started = monotonic()
        result = ExtractionService.extract(
            transcript=record.voice_transcript,
            record=record,
        )
        record.customer_name = str(
            result.data.get("customer_name") or record.customer_name,
        )
        record.product = str(result.data.get("product") or record.product)
        record.quantity = int(result.data.get("quantity") or record.quantity)
        record.amount = result.data.get("amount", record.amount)
        record.currency = str(result.data.get("currency") or record.currency)
        record.payment_method = str(
            result.data.get("payment_method") or record.payment_method,
        )
        record.confidence_score = result.confidence_score
        record.ai_extraction_provider = result.provider
        record.ai_prompt_version = result.prompt_version
        record.status = Record.Status.EXTRACTED
        record.save(
            update_fields=[
                "customer_name",
                "product",
                "quantity",
                "amount",
                "currency",
                "payment_method",
                "confidence_score",
                "ai_extraction_provider",
                "ai_prompt_version",
                "status",
                "updated_at",
            ],
        )
        duration = monotonic() - started
        UsageTrackingService.log_ai_usage(
            record=record,
            provider=result.provider,
            service_type=AIUsage.ServiceType.EXTRACTION,
            duration_seconds=duration,
        )
        _append_processing_state(
            record,
            Record.Status.EXTRACTED,
            {
                "provider": result.provider,
                "model": result.model,
                "prompt_version": result.prompt_version,
                "duration_seconds": duration,
            },
        )
        return

    if step == "store":
        RecordProcessingService.store(record)
        _append_processing_state(record, Record.Status.STORED)
        return

    msg = f"Unsupported processing step: {step}"
    raise ValueError(msg)


def _execute_with_retries(*, record: Record, step: str) -> None:
    for attempt in range(1, MAX_STEP_RETRIES + 1):
        try:
            _run_step(record=record, step=step)
            if record.processing_error_step == step:
                record.processing_error = ""
                record.processing_error_step = ""
                record.save(
                    update_fields=[
                        "processing_error",
                        "processing_error_step",
                        "updated_at",
                    ],
                )
        except Exception as exc:
            record.processing_error = str(exc)
            record.processing_error_step = step
            record.processing_retry_count += 1
            record.last_failed_at = timezone.now()
            record.status = Record.Status.FAILED
            record.save(
                update_fields=[
                    "status",
                    "processing_error",
                    "processing_error_step",
                    "processing_retry_count",
                    "last_failed_at",
                    "updated_at",
                ],
            )
            _append_processing_state(
                record,
                Record.Status.FAILED,
                {"step": step, "attempt": attempt, "error": str(exc)},
            )
            if attempt >= MAX_STEP_RETRIES:
                record.status = Record.Status.DEAD_LETTER
                record.dead_lettered_at = timezone.now()
                record.save(update_fields=["status", "dead_lettered_at", "updated_at"])
                _append_processing_state(
                    record,
                    Record.Status.DEAD_LETTER,
                    {"step": step, "error": str(exc)},
                )
                _notify_record_failed(record, str(exc))
                raise
        else:
            return


@shared_task
def process_whatsapp_record(
    record_id: int,
    payload_id: int | None = None,
    *,
    force_reprocess: bool = False,
) -> None:
    record = Record.objects.get(pk=record_id)
    if record.status == Record.Status.STORED and not force_reprocess:
        return

    if force_reprocess:
        record.status = Record.Status.RECEIVED
        record.processing_error = ""
        record.processing_error_step = ""
        record.dead_lettered_at = None
        record.save(
            update_fields=[
                "status",
                "processing_error",
                "processing_error_step",
                "dead_lettered_at",
                "updated_at",
            ],
        )
        _append_processing_state(
            record,
            Record.Status.RECEIVED,
            {"force_reprocess": True},
        )

    try:
        _execute_with_retries(record=record, step="transcribe")
        _execute_with_retries(record=record, step="extract")
        _execute_with_retries(record=record, step="store")
        if payload_id is not None:
            WhatsAppRawPayload.objects.filter(pk=payload_id).update(
                processed=True,
                processed_at=timezone.now(),
            )
    except Exception as exc:
        if record.status != Record.Status.DEAD_LETTER:
            record.status = Record.Status.FAILED
            record.processing_error = str(exc)
            record.save(
                update_fields=[
                    "status",
                    "processing_error",
                    "processing_error_step",
                    "updated_at",
                ],
            )
        raise


@shared_task
def replay_whatsapp_payload(payload_id: int) -> None:
    payload = WhatsAppRawPayload.objects.select_related("organization").get(
        pk=payload_id,
    )
    message_id = payload.message_id
    record, _ = Record.objects.get_or_create(
        source=Record.Source.WHATSAPP,
        source_reference=message_id,
        defaults={
            "organization": payload.organization,
            "status": Record.Status.RECEIVED,
            "customer_name": "Unknown customer",
            "product": "WhatsApp voice note",
            "quantity": 1,
            "amount": 0,
            "currency": payload.organization.default_currency or "USD",
            "audio_url": payload.media_url,
        },
    )
    process_whatsapp_record.delay(
        record.pk,
        payload.pk,
        force_reprocess=True,
    )
