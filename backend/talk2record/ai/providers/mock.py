from __future__ import annotations

from decimal import Decimal

from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.base import TranscriptionResult


class MockTranscriptionProvider:
    provider_name = "mock"
    model_name = "mock-transcriber-v1"

    def transcribe(
        self,
        *,
        audio_url: str,
        audio_bytes: bytes | None = None,
        context_label: str = "",
    ) -> TranscriptionResult:
        label = context_label or "unknown customer"
        transcript = (
            f"Structured transcript placeholder for {label}. "
            f"Audio source: {audio_url or 'no-audio-url-provided'}."
        )
        return TranscriptionResult(
            transcript=transcript,
            provider=self.provider_name,
            model=self.model_name,
        )


class MockExtractionProvider:
    """In-memory extraction provider for tests and offline development."""

    provider_name = "mock"
    model_name = "mock-extractor-v1"

    def extract(
        self,
        *,
        transcript: str,
        context: dict,
        prompt_version: str,
        system_prompt: str = "",
        user_prompt: str = "",
    ) -> ExtractionResult:
        data: dict = {
            "transcript": transcript,
            **{k: v for k, v in context.items() if k not in {"prompt", "schema"}},
        }
        return ExtractionResult(
            data=data,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.900"),
        )
