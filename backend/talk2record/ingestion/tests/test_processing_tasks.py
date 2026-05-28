from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import AI_TRANSCRIPTION_COMPLETED
from talk2record.events.names import RECORD_PROCESSING_COMPLETED
from talk2record.events.names import RECORD_PROCESSING_STARTED
from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.ingestion.tasks import MAX_STEP_RETRIES
from talk2record.ingestion.tasks import process_whatsapp_record
from talk2record.ingestion.tasks import replay_whatsapp_payload
from talk2record.records.models import Record
from talk2record.records.models import RecordArtifact
from talk2record.records.models import RecordProcessingState
from talk2record.usage.models import AIUsage
from talk2record.usage.services import AIUsageQuotaExceededError
from talk2record.usage.services import UsageTrackingService


@pytest.mark.django_db(transaction=True)
def test_process_whatsapp_record_marks_payload_processed(settings, record):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    raw_payload = WhatsAppRawPayload.objects.create(
        organization=record.organization,
        message_id=f"wamid.process.{record.pk}",
        payload={"entry": []},
    )
    record.source = Record.Source.WHATSAPP
    record.source_reference = raw_payload.message_id
    record.status = Record.Status.RECEIVED
    record.save(update_fields=["source", "source_reference", "status", "updated_at"])

    process_whatsapp_record(record.pk, raw_payload.pk)

    record.refresh_from_db()
    raw_payload.refresh_from_db()
    assert record.status == Record.Status.STORED

    # Artifacts replace direct fields
    transcript_artifact = record.artifacts.filter(key="transcript").first()
    assert transcript_artifact is not None
    assert transcript_artifact.provider == "mock"

    extraction_artifact = record.artifacts.filter(key="extraction").first()
    assert extraction_artifact is not None
    assert extraction_artifact.provider == "mock"
    assert extraction_artifact.prompt_version == "v1"

    assert record.processing_states.filter(status=Record.Status.TRANSCRIBED).exists()
    assert record.processing_states.filter(status=Record.Status.EXTRACTED).exists()
    assert record.processing_states.filter(status=Record.Status.STORED).exists()
    assert record.ai_usage.filter(
        service_type=AIUsage.ServiceType.TRANSCRIPTION,
    ).exists()
    assert record.ai_usage.filter(service_type=AIUsage.ServiceType.EXTRACTION).exists()
    assert raw_payload.processed is True
    assert raw_payload.processed_at is not None


@pytest.mark.django_db(transaction=True)
def test_process_whatsapp_record_emits_ai_transcription_event_not_direct_call(
    settings,
    record,
):
    """transcribe step emits AI_TRANSCRIPTION_COMPLETED event; UsageTrackingService logs via event handler."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    raw_payload = WhatsAppRawPayload.objects.create(
        organization=record.organization,
        message_id=f"wamid.event.{record.pk}",
        payload={"entry": []},
    )
    record.source = Record.Source.WHATSAPP
    record.source_reference = raw_payload.message_id
    record.status = Record.Status.RECEIVED
    record.save(update_fields=["source", "source_reference", "status", "updated_at"])

    captured_events: list[str] = []

    original_publish = __import__(
        "talk2record.events.bus",
        fromlist=["publish_after_commit"],
    ).publish_after_commit

    def capturing_publish(event):
        captured_events.append(event.name)
        return original_publish(event)

    with patch("talk2record.ingestion.tasks.publish_after_commit", capturing_publish):
        process_whatsapp_record(record.pk, raw_payload.pk)

    assert AI_TRANSCRIPTION_COMPLETED in captured_events
    assert RECORD_PROCESSING_STARTED in captured_events
    assert RECORD_PROCESSING_COMPLETED in captured_events
    assert DomainEventRecord.objects.filter(name=AI_TRANSCRIPTION_COMPLETED).exists()
    assert record.ai_usage.filter(
        service_type=AIUsage.ServiceType.TRANSCRIPTION,
    ).exists()


@pytest.mark.django_db
def test_process_whatsapp_record_dead_letters_after_retries(monkeypatch, record):
    record.source = Record.Source.WHATSAPP
    record.source_reference = f"wamid.deadletter.{record.pk}"
    record.status = Record.Status.RECEIVED
    record.save(update_fields=["source", "source_reference", "status", "updated_at"])

    def fail_transcribe(_cls, _record, **kwargs):
        msg = "transcription provider down"
        raise RuntimeError(msg)

    monkeypatch.setattr(
        "talk2record.ingestion.tasks.TranscriptionService.transcribe",
        classmethod(fail_transcribe),
    )

    with pytest.raises(RuntimeError):
        process_whatsapp_record(record.pk)

    record.refresh_from_db()
    assert record.status == Record.Status.DEAD_LETTER
    assert record.processing_error_step == "transcribe"
    assert record.processing_retry_count == MAX_STEP_RETRIES
    assert record.last_failed_at is not None
    assert record.dead_lettered_at is not None
    assert (
        record.processing_states.filter(status=Record.Status.FAILED).count()
        == MAX_STEP_RETRIES
    )
    assert (
        record.processing_states.filter(status=Record.Status.DEAD_LETTER).count() == 1
    )


@pytest.mark.django_db
def test_replay_whatsapp_payload_queues_reprocess(monkeypatch, organization):
    raw_payload = WhatsAppRawPayload.objects.create(
        organization=organization,
        message_id="wamid.replay.1",
        payload={"entry": [{"changes": []}]},
        media_url="https://example.com/audio/replay.ogg",
        processed=True,
        processed_at=timezone.now(),
    )
    record = Record.objects.create(
        organization=organization,
        source=Record.Source.WHATSAPP,
        source_reference=raw_payload.message_id,
        status=Record.Status.FAILED,
        type=Record.Type.VOICE_NOTE,
    )
    queued: list[tuple[int, int | None, bool]] = []

    def fake_delay(record_id: int, payload_id: int | None, **kwargs):
        force_reprocess = bool(kwargs.get("force_reprocess"))
        queued.append((record_id, payload_id, force_reprocess))

    monkeypatch.setattr(
        "talk2record.ingestion.tasks.process_whatsapp_record.delay",
        fake_delay,
    )

    replay_whatsapp_payload(raw_payload.pk)

    assert queued == [(record.pk, raw_payload.pk, True)]


@pytest.mark.django_db
def test_processing_state_model_str(record):
    state = RecordProcessingState.objects.create(
        record=record,
        status=Record.Status.RECEIVED,
    )
    assert str(state) == f"{record.pk}:{Record.Status.RECEIVED}"


@pytest.mark.django_db(transaction=True)
def test_process_whatsapp_record_enforces_ai_usage_quota(settings, record):
    settings.AI_USAGE_MONTHLY_LIMIT_PER_ORG = 1
    settings.CELERY_TASK_ALWAYS_EAGER = True
    record.source = Record.Source.WHATSAPP
    record.source_reference = f"wamid.quota.{record.pk}"
    record.status = Record.Status.RECEIVED
    record.save(update_fields=["source", "source_reference", "status", "updated_at"])

    with pytest.raises(AIUsageQuotaExceededError):
        process_whatsapp_record(record.pk)

    record.refresh_from_db()
    # Quota exceeded is a permanent failure → dead-lettered immediately
    assert record.status in {Record.Status.FAILED, Record.Status.DEAD_LETTER}
    assert record.processing_error_step == "extract_quota"
    assert UsageTrackingService.monthly_usage_count(record.organization) == 1
    assert (
        record.ai_usage.filter(service_type=AIUsage.ServiceType.TRANSCRIPTION).count()
        == 1
    )
    assert (
        record.ai_usage.filter(service_type=AIUsage.ServiceType.EXTRACTION).count() == 0
    )


@pytest.mark.django_db(transaction=True)
def test_process_whatsapp_record_writes_artifacts(settings, record):
    """Pipeline writes transcript + extraction artifacts — never sets direct AI fields on Record."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    record.source_reference = f"wamid.artifacts.{record.pk}"
    record.save(update_fields=["source_reference", "updated_at"])

    process_whatsapp_record(record.pk)

    assert RecordArtifact.objects.filter(record=record, key="transcript").exists()
    assert RecordArtifact.objects.filter(record=record, key="extraction").exists()

    transcript_artifact = RecordArtifact.objects.get(record=record, key="transcript")
    assert "text" in transcript_artifact.content
    assert transcript_artifact.artifact_type == RecordArtifact.ArtifactType.TEXT


@pytest.mark.django_db(transaction=True)
def test_process_whatsapp_record_skips_already_stored(settings, record):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    record.status = Record.Status.STORED
    record.save(update_fields=["status", "updated_at"])

    process_whatsapp_record(record.pk)

    record.refresh_from_db()
    assert record.status == Record.Status.STORED
    assert not RecordArtifact.objects.filter(record=record).exists()
