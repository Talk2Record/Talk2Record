from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from talk2record.ai.providers.mock import MockTranscriptionProvider

if TYPE_CHECKING:
    from talk2record.ai.providers.base import BaseTranscriptionProvider
    from talk2record.ai.providers.base import TranscriptionResult
    from talk2record.records.models import Record


class TranscriptionService:
    _providers: dict[str, BaseTranscriptionProvider] = {
        "mock": MockTranscriptionProvider(),
    }

    @classmethod
    def _provider(cls) -> BaseTranscriptionProvider:
        configured = getattr(settings, "AI_TRANSCRIPTION_PROVIDER", "mock")
        return cls._providers.get(configured, cls._providers["mock"])

    @classmethod
    def transcribe(cls, record: Record) -> TranscriptionResult:
        provider = cls._provider()
        return provider.transcribe(
            audio_url=record.audio_url,
            context_label=f"{record.customer_name} and {record.product}",
        )
