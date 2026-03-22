from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from talk2record.ai.providers.mock import MockTranscriptionProvider
from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret

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
        integration = get_active_integration("ai")
        configured = ""
        if integration is not None:
            configured = str(
                integration.config.get("transcription_provider")
                or integration.config.get("provider")
                or "",
            ).strip()
            # Resolve secret at runtime so admin key updates take effect immediately.
            get_active_integration_secret("ai")
        if not configured:
            configured = getattr(settings, "AI_TRANSCRIPTION_PROVIDER", "mock")
        return cls._providers.get(configured, cls._providers["mock"])

    @classmethod
    def transcribe(cls, record: Record) -> TranscriptionResult:
        provider = cls._provider()
        return provider.transcribe(
            audio_url=record.audio_url,
            context_label=f"{record.customer_name} and {record.product}",
        )
