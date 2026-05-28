from __future__ import annotations

from decimal import Decimal
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.db import transaction
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import RECORD_STORED
from talk2record.notifications.services import NotificationService
from talk2record.records.models import Record
from talk2record.records.models import RecordArtifact
from talk2record.records.services import RecordProcessingService


@pytest.mark.django_db
def test_record_str(record):
    assert (
        str(record)
        == f"{record.organization.name}: {record.source_reference or record.pk}"
    )


@pytest.mark.django_db
def test_record_type_field_defaults_to_voice_note(record):
    assert record.type == Record.Type.VOICE_NOTE


@pytest.mark.django_db
def test_record_has_no_ai_fields(record):
    """Record is a clean container — no AI-specific fields."""
    assert not hasattr(record, "voice_transcript")
    assert not hasattr(record, "customer_name")
    assert not hasattr(record, "product")
    assert not hasattr(record, "ai_transcription_provider")


@pytest.mark.django_db
def test_record_get_artifact_returns_none_when_absent(record):
    assert record.get_artifact("transcript") is None


@pytest.mark.django_db
def test_record_get_artifact_returns_artifact(record):
    artifact = RecordArtifact.objects.create(
        record=record,
        key="transcript",
        artifact_type=RecordArtifact.ArtifactType.TEXT,
        content={"text": "hello"},
    )
    assert record.get_artifact("transcript") == artifact


@pytest.mark.django_db
def test_record_artifact_str(record):
    artifact = RecordArtifact.objects.create(
        record=record,
        key="extraction",
        artifact_type=RecordArtifact.ArtifactType.JSON,
        content={"customer_name": "Kifaru"},
    )
    assert str(artifact) == f"{record.pk}:extraction"


@pytest.mark.django_db(transaction=True)
def test_record_processing_service_store_sets_status_and_fires_event(settings, record):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    with transaction.atomic():
        stored = RecordProcessingService.store(record)

    stored.refresh_from_db()
    assert stored.status == Record.Status.STORED
    assert AuditLog.objects.filter(action=RECORD_STORED).exists()
    assert Event.objects.filter(name="record_stored").exists()
    assert DomainEventRecord.objects.filter(name=RECORD_STORED).exists()


@pytest.mark.django_db
def test_record_processing_service_does_not_call_notification_service_directly(record):
    """store() must only emit an event — direct NotificationService.create call removed."""
    record.status = Record.Status.EXTRACTED
    record.save()

    with patch("talk2record.records.services.publish_after_commit"):
        with patch.object(NotificationService, "create") as mock_create:
            RecordProcessingService.store(record)

    mock_create.assert_not_called()


@pytest.mark.django_db
def test_record_processing_service_save_transcript_artifact(record):
    from talk2record.ai.providers.base import TranscriptionResult

    result = TranscriptionResult(
        transcript="Hello from mock",
        provider="mock",
        model="mock-v1",
    )
    artifact = RecordProcessingService.save_transcript_artifact(record, result)

    assert artifact.key == "transcript"
    assert artifact.content["text"] == "Hello from mock"
    assert artifact.provider == "mock"
    assert record.get_artifact("transcript") == artifact


@pytest.mark.django_db
def test_record_processing_service_save_extraction_artifact(record):
    from talk2record.ai.providers.base import ExtractionResult

    result = ExtractionResult(
        data={"customer_name": "Kifaru", "product": "Oil"},
        provider="mock",
        model="mock-v1",
        prompt_version="v1",
        confidence_score=Decimal("0.950"),
    )
    artifact = RecordProcessingService.save_extraction_artifact(record, result)

    assert artifact.key == "extraction"
    assert artifact.content["customer_name"] == "Kifaru"
    assert artifact.prompt_version == "v1"


@pytest.mark.django_db
def test_record_processing_service_get_transcript_from_artifact(record):
    RecordArtifact.objects.create(
        record=record,
        key="transcript",
        artifact_type=RecordArtifact.ArtifactType.TEXT,
        content={"text": "test transcript"},
    )
    assert RecordProcessingService.get_transcript(record) == "test transcript"


@pytest.mark.django_db
def test_record_processing_service_get_transcript_returns_empty_when_absent(record):
    assert RecordProcessingService.get_transcript(record) == ""


@pytest.mark.django_db
def test_record_admin_page(admin_client, record):
    response = admin_client.get(reverse("admin:records_record_changelist"))

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_reprocess_dead_letter_record(workspace_user, record):
    client = APIClient()
    client.force_authenticate(user=workspace_user)
    record.status = Record.Status.DEAD_LETTER
    record.processing_error = "Invalid URL '/media/voice_notes/3/1.webm'"
    record.processing_error_step = "transcribe"
    record.processing_retry_count = 3
    record.audio_url = "/media/voice_notes/3/1.webm"
    record.save()

    with patch("talk2record.records.views.process_whatsapp_record.delay") as mock_delay:
        response = client.post(
            reverse("api:record-reprocess", kwargs={"pk": record.pk}),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    mock_delay.assert_called_once()
    args, kwargs = mock_delay.call_args
    assert args[0] == record.pk
    assert kwargs["force_reprocess"] is True

    record.refresh_from_db()
    assert record.processing_retry_count == 0


@pytest.mark.django_db
def test_reprocess_review_record(workspace_user, record):
    client = APIClient()
    client.force_authenticate(user=workspace_user)
    record.status = Record.Status.REVIEW
    record.audio_url = "/media/voice_notes/3/1.webm"
    record.save()

    with patch("talk2record.records.views.process_whatsapp_record.delay") as mock_delay:
        response = client.post(
            reverse("api:record-reprocess", kwargs={"pk": record.pk}),
        )

    assert response.status_code == HTTPStatus.ACCEPTED
    mock_delay.assert_called_once()


@pytest.mark.django_db
def test_reprocess_rejects_stored_record(workspace_user, record):
    client = APIClient()
    client.force_authenticate(user=workspace_user)
    record.status = Record.Status.STORED
    record.save()

    response = client.post(reverse("api:record-reprocess", kwargs={"pk": record.pk}))

    assert response.status_code == HTTPStatus.BAD_REQUEST
