from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    from decimal import Decimal

DEFAULT_EXTRACTION_SYSTEM_PROMPT = (
    "You are a data extraction assistant. Return only valid JSON."
)


@dataclass(frozen=True)
class TranscriptionResult:
    transcript: str
    provider: str
    model: str


@dataclass(frozen=True)
class ExtractionResult:
    data: dict
    provider: str
    model: str
    prompt_version: str
    confidence_score: Decimal


class BaseTranscriptionProvider(Protocol):
    provider_name: str
    model_name: str

    def transcribe(
        self,
        *,
        audio_url: str,
        audio_bytes: bytes | None = None,
        context_label: str = "",
    ) -> TranscriptionResult:
        raise NotImplementedError


class BaseExtractionProvider(Protocol):
    provider_name: str
    model_name: str

    def extract(
        self,
        *,
        transcript: str,
        context: dict,
        prompt_version: str,
        system_prompt: str = "",
        user_prompt: str = "",
    ) -> ExtractionResult:
        """Run extraction against the given transcript.

        ``system_prompt`` and ``user_prompt`` are resolved by
        :class:`~talk2record.taxonomy.services.prompt_resolver.PromptResolver`.
        When empty, providers use :data:`DEFAULT_EXTRACTION_SYSTEM_PROMPT`.
        """

        raise NotImplementedError
