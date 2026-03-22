from __future__ import annotations

from decimal import Decimal

import pytest

from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration
from talk2record.ai.models import AIPromptTemplate
from talk2record.ai.services.extraction import ExtractionService
from talk2record.ai.services.transcription import TranscriptionService


@pytest.mark.django_db
def test_transcription_service_uses_mock_provider(record):
    result = TranscriptionService.transcribe(record)

    assert result.provider == "mock"
    assert result.model == "mock-transcriber-v1"
    assert "Structured transcript placeholder" in result.transcript


@pytest.mark.django_db
def test_extraction_service_validates_and_returns_metadata(record):
    transcript = "Customer wants delivery tomorrow."
    result = ExtractionService.extract(transcript=transcript, record=record)

    assert result.provider == "mock"
    assert result.model == "mock-extractor-v1"
    assert result.prompt_version == "v1"
    assert result.confidence_score == Decimal("0.950")
    assert result.data["voice_transcript"] == transcript


@pytest.mark.django_db
def test_extraction_uses_latest_prompt_template_version(record):
    AIPromptTemplate.objects.create(
        name="record_extraction",
        provider="mock",
        model="mock-extractor-v1",
        prompt_text="extract structured payload",
        version=3,
    )
    transcript = "Need to extract values."

    result = ExtractionService.extract(transcript=transcript, record=record)

    assert result.prompt_version == "v3"


@pytest.mark.django_db
def test_ai_services_use_global_integration_runtime_config(record):
    integration = Integration.objects.create(
        slug="ai",
        enabled=True,
        config={"provider": "mock"},
    )
    ApiCredential.objects.create(
        integration=integration,
        encrypted_secret=SecretVault.encrypt("ai-secret"),
    )

    transcription = TranscriptionService.transcribe(record)
    extraction = ExtractionService.extract(transcript=transcription.transcript, record=record)

    assert transcription.provider == "mock"
    assert extraction.provider == "mock"
