from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from talk2record.ai.providers.mock import MockTranscriptionProvider
from talk2record.ai.runtime import get_active_ai_settings
from talk2record.ai.runtime import get_ai_credential_plaintext

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
        settings_row = get_active_ai_settings()
        configured = ""
        if settings_row is not None:
            cfg = settings_row.config if isinstance(settings_row.config, dict) else {}
            configured = str(
                cfg.get("transcription_provider")
                or cfg.get("provider")
                or "",
            ).strip()
            get_ai_credential_plaintext()
        if not configured:
            configured = getattr(settings, "AI_TRANSCRIPTION_PROVIDER", "mock")
        return cls._providers.get(configured, cls._providers["mock"])

    @classmethod
    def transcribe(cls, record: Record, *, resolved_audio_url: str = "") -> TranscriptionResult:
        provider = cls._provider()
        audio_url = resolved_audio_url or record.audio_url
        context_label = record.source_reference or str(record.pk)
        return provider.transcribe(
            audio_url=audio_url,
            context_label=context_label,
        )
