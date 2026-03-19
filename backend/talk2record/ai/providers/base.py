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
    ) -> ExtractionResult:
        raise NotImplementedError
