from __future__ import annotations

from time import monotonic
from uuid import uuid4

from celery import shared_task
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone

from talk2record.ai.services.extraction import ExtractionService
from talk2record.ai.services.transcription import TranscriptionService
from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import AI_EXTRACTION_COMPLETED
from talk2record.events.names import AI_EXTRACTION_FAILED
from talk2record.events.names import AI_EXTRACTION_STARTED
from talk2record.events.names import AI_TRANSCRIPTION_COMPLETED
from talk2record.events.names import AI_TRANSCRIPTION_FAILED
from talk2record.events.names import AI_TRANSCRIPTION_STARTED
from talk2record.events.names import RECORD_PROCESSING_COMPLETED
from talk2record.events.names import RECORD_PROCESSING_FAILED
from talk2record.events.names import RECORD_PROCESSING_STARTED
from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.ingestion.observability import log_ingestion_event
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.records.models import Record
from talk2record.records.models import RecordProcessingState
from talk2record.records.services import RecordProcessingService
from talk2record.usage.models import AIUsage
from talk2record.usage.services import AIUsageQuotaExceededError
from talk2record.usage.services import UsageTrackingService
from talk2record.whatsapp.media import WhatsAppMediaService

MAX_STEP_RETRIES = 3


class ProcessingStepRunner:
    """
    Orchestrates the three-step transcribe → extract → store pipeline for a
    single Record.  Each step is executed with retry logic; permanent failures
    dead-letter the record.

    Single Responsibility: step execution, retry management, and lifecycle
    event publishing.  Domain concerns (artifact persistence, store event) live
    in RecordProcessingService.
    """

    def __init__(self, record: Record, request_id: str = "", event_id: str = "") -> None:
        self.record = record
        self.request_id = request_id or str(uuid4())
        self.event_id = event_id or str(uuid4())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Execute pipeline steps in order: download → transcribe → extract → store."""
        self._execute_with_retries("download_media")
        self._execute_with_retries("transcribe")
        self._execute_with_retries("extract")
        self._execute_with_retries("store")

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _run_step(self, step: str) -> None:
        if step == "download_media":
            self._step_download_media()
        elif step == "transcribe":
            self._step_transcribe()
        elif step == "extract":
            self._step_extract()
        elif step == "store":
            self._step_store()
        else:
            msg = f"Unsupported processing step: {step}"
            raise ValueError(msg)

    def _step_download_media(self) -> None:
        """Download WhatsApp voice note from the Graph API and persist to storage.

        Skipped when:
        - The record is not from WhatsApp.
        - The record already has an audio_url (downloaded previously or supplied directly).
        - WhatsApp access token is not configured (graceful skip; mock transcription proceeds).
        """
        from talk2record.whatsapp.config import load_whatsapp_cloud_settings  # noqa: PLC0415

        record = self.record
        if record.source != Record.Source.WHATSAPP:
            return
        if not record.media_id or record.audio_url:
            return

        wa_settings = load_whatsapp_cloud_settings()
        if wa_settings is None or not wa_settings.access_token:
            return

        signed_url = WhatsAppMediaService.resolve_and_get_url(record.media_id)
        audio_bytes = WhatsAppMediaService.download_media(signed_url)

        filename = f"voice_notes/{record.organization_id}/{record.pk}.ogg"
        saved_path = default_storage.save(filename, ContentFile(audio_bytes))
        record.audio_url = default_storage.url(saved_path)
        record.save(update_fields=["audio_url", "updated_at"])

    def _step_transcribe(self) -> None:
        record = self.record
        UsageTrackingService.enforce_monthly_usage_limit(record.organization)

        record.status = Record.Status.TRANSCRIBING
        record.save(update_fields=["status", "updated_at"])
        self._append_state(Record.Status.TRANSCRIBING)

        publish_after_commit(
            DomainEvent(
                name=AI_TRANSCRIPTION_STARTED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={"request_id": self.request_id},
            ),
        )

        started = monotonic()
        result = TranscriptionService.transcribe(record)
        duration = monotonic() - started

        RecordProcessingService.save_transcript_artifact(record, result)
        record.status = Record.Status.TRANSCRIBED
        record.save(update_fields=["status", "updated_at"])

        publish_after_commit(
            DomainEvent(
                name=AI_TRANSCRIPTION_COMPLETED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "provider": result.provider,
                    "service_type": AIUsage.ServiceType.TRANSCRIPTION,
                    "duration_seconds": duration,
                    "model": result.model,
                },
            ),
        )
        self._append_state(
            Record.Status.TRANSCRIBED,
            {"provider": result.provider, "model": result.model, "duration_seconds": duration},
        )

    def _step_extract(self) -> None:
        record = self.record
        UsageTrackingService.enforce_monthly_usage_limit(record.organization)

        record.status = Record.Status.EXTRACTING
        record.save(update_fields=["status", "updated_at"])
        self._append_state(Record.Status.EXTRACTING)

        publish_after_commit(
            DomainEvent(
                name=AI_EXTRACTION_STARTED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={"request_id": self.request_id},
            ),
        )

        transcript = RecordProcessingService.get_transcript(record)
        started = monotonic()
        result = ExtractionService.extract(
            transcript=transcript,
            organization=record.organization,
        )
        duration = monotonic() - started

        RecordProcessingService.save_extraction_artifact(record, result)
        record.status = Record.Status.EXTRACTED
        record.save(update_fields=["status", "updated_at"])

        publish_after_commit(
            DomainEvent(
                name=AI_EXTRACTION_COMPLETED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "provider": result.provider,
                    "service_type": AIUsage.ServiceType.EXTRACTION,
                    "duration_seconds": duration,
                    "model": result.model,
                    "prompt_version": result.prompt_version,
                },
            ),
        )
        self._append_state(
            Record.Status.EXTRACTED,
            {
                "provider": result.provider,
                "model": result.model,
                "prompt_version": result.prompt_version,
                "duration_seconds": duration,
            },
        )

    def _step_store(self) -> None:
        RecordProcessingService.store(self.record)
        self._append_state(Record.Status.STORED)

    # ------------------------------------------------------------------
    # Retry / failure handling
    # ------------------------------------------------------------------

    def _execute_with_retries(self, step: str) -> None:
        for attempt in range(1, MAX_STEP_RETRIES + 1):
            try:
                self._run_step(step)
            except AIUsageQuotaExceededError as exc:
                self._mark_failed(step=f"{step}_quota", error=str(exc), permanent=True)
                raise
            except Exception as exc:
                self.record.processing_retry_count += 1
                permanent = attempt >= MAX_STEP_RETRIES
                self._mark_failed(step=step, error=str(exc), permanent=permanent)
                if permanent:
                    raise
            else:
                # Clear any previous error info on success
                if self.record.processing_error_step == step:
                    self.record.processing_error = ""
                    self.record.processing_error_step = ""
                    self.record.save(
                        update_fields=["processing_error", "processing_error_step", "updated_at"],
                    )
                return

    def _mark_failed(self, *, step: str, error: str, permanent: bool) -> None:
        record = self.record
        record.processing_error = error
        record.processing_error_step = step
        record.status = Record.Status.FAILED
        record.last_failed_at = timezone.now()
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
        self._append_state(
            Record.Status.FAILED,
            {"step": step, "error": error, "permanent": permanent},
        )

        if permanent:
            record.status = Record.Status.DEAD_LETTER
            record.dead_lettered_at = timezone.now()
            record.save(update_fields=["status", "dead_lettered_at", "updated_at"])
            self._append_state(Record.Status.DEAD_LETTER, {"step": step, "error": error})
            self._notify_failed(error)

    def _notify_failed(self, error: str) -> None:
        record = self.record
        if record.created_by_id:
            NotificationService.create(
                user=record.created_by,
                notification_type=Notification.Type.RECORD_FAILED,
                title="Voice note processing failed",
                message=error or "An error occurred while processing your voice note.",
                organization=record.organization,
                metadata={"record_id": record.pk},
            )

    def _append_state(self, status: str, details: dict | None = None) -> None:
        RecordProcessingState.objects.create(
            record=self.record,
            status=status,
            details=details or {},
        )
        NotificationService.broadcast_record_event(
            organization=self.record.organization,
            record_id=self.record.pk,
            status=status,
            event_type="record_updated",
            summary="Record processing status changed.",
        )


# ---------------------------------------------------------------------------
# Celery tasks
# ---------------------------------------------------------------------------


@shared_task
def process_whatsapp_record(
    record_id: int,
    payload_id: int | None = None,
    *,
    force_reprocess: bool = False,
    request_id: str = "",
    event_id: str = "",
) -> None:
    normalized_request_id = request_id or str(uuid4())
    normalized_event_id = event_id or str(uuid4())
    record = Record.objects.get(pk=record_id)

    if record.status == Record.Status.STORED and not force_reprocess:
        log_ingestion_event(
            "processing.record.skipped",
            request_id=normalized_request_id,
            event_id=normalized_event_id,
            task_id="sync",
            record_id=record.pk,
            org_id=record.organization_id,
            reason="already_stored",
        )
        return

    runner = ProcessingStepRunner(
        record=record,
        request_id=normalized_request_id,
        event_id=normalized_event_id,
    )

    if force_reprocess:
        record.status = Record.Status.RECEIVED
        record.processing_error = ""
        record.processing_error_step = ""
        record.processing_retry_count = 0
        record.dead_lettered_at = None
        record.save(
            update_fields=[
                "status",
                "processing_error",
                "processing_error_step",
                "processing_retry_count",
                "dead_lettered_at",
                "updated_at",
            ],
        )
        runner._append_state(Record.Status.RECEIVED, {"force_reprocess": True})
        log_ingestion_event(
            "processing.record.reprocess_started",
            request_id=normalized_request_id,
            event_id=normalized_event_id,
            task_id="sync",
            record_id=record.pk,
            org_id=record.organization_id,
        )

    try:
        log_ingestion_event(
            "processing.record.started",
            request_id=normalized_request_id,
            event_id=normalized_event_id,
            task_id="sync",
            record_id=record.pk,
            org_id=record.organization_id,
        )
        publish_after_commit(
            DomainEvent(
                name=RECORD_PROCESSING_STARTED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={"request_id": normalized_request_id},
            ),
        )

        runner.run()

        if payload_id is not None:
            WhatsAppRawPayload.objects.filter(pk=payload_id).update(
                processed=True,
                processed_at=timezone.now(),
            )

        publish_after_commit(
            DomainEvent(
                name=RECORD_PROCESSING_COMPLETED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={"request_id": normalized_request_id, "status": record.status},
            ),
        )
        log_ingestion_event(
            "processing.record.completed",
            request_id=normalized_request_id,
            event_id=normalized_event_id,
            task_id="sync",
            record_id=record.pk,
            org_id=record.organization_id,
            status=record.status,
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
        publish_after_commit(
            DomainEvent(
                name=RECORD_PROCESSING_FAILED,
                organization_id=record.organization_id,
                user_id=record.created_by_id,
                resource_type="record",
                resource_id=str(record.pk),
                metadata={
                    "request_id": normalized_request_id,
                    "error": str(exc),
                    "failed_step": record.processing_error_step,
                },
            ),
        )
        log_ingestion_event(
            "processing.record.failed",
            request_id=normalized_request_id,
            event_id=normalized_event_id,
            task_id="sync",
            record_id=record.pk,
            org_id=record.organization_id,
            status=record.status,
            error=str(exc),
            failed_step=record.processing_error_step,
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
            "audio_url": payload.media_url,
            "media_id": payload.media_id,
        },
    )
    process_whatsapp_record.delay(
        record.pk,
        payload.pk,
        force_reprocess=True,
        event_id=str(uuid4()),
    )
