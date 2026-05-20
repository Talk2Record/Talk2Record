from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import Protocol

if TYPE_CHECKING:
    from decimal import Decimal


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

        ``system_prompt`` and ``user_prompt`` are the resolved prompt bodies
        from the taxonomy ``PromptResolver`` with all placeholders already
        filled in. They are optional so legacy callers (the sales-flavored
        :class:`ExtractionService`) keep working; in that case the provider
        falls back to its built-in legacy prompt.
        """

        raise NotImplementedError
