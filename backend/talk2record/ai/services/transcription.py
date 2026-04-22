from __future__ import annotations

from typing import TYPE_CHECKING

from talk2record.ai.models import AITask
from talk2record.ai.providers.mock import MockTranscriptionProvider
from talk2record.ai.resolver import resolve

if TYPE_CHECKING:
    from talk2record.ai.providers.base import BaseTranscriptionProvider
    from talk2record.ai.providers.base import TranscriptionResult
    from talk2record.organizations.models import Organization
    from talk2record.records.models import Record


class TranscriptionService:
    @classmethod
    def _provider(cls, organization: Organization | None = None) -> BaseTranscriptionProvider:
        resolution = resolve(task=AITask.TRANSCRIPTION, organization=organization)
        if resolution is None or resolution.spec.transcription_factory is None:
            return MockTranscriptionProvider()
        return resolution.build_transcription_provider()

    @classmethod
    def transcribe(cls, record: Record, *, resolved_audio_url: str = "") -> TranscriptionResult:
        organization = record.organization if record.organization_id else None
        provider = cls._provider(organization=organization)
        audio_url = resolved_audio_url or record.audio_url
        context_label = record.source_reference or str(record.pk)
        return provider.transcribe(
            audio_url=audio_url,
            context_label=context_label,
        )
