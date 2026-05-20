from __future__ import annotations

import io
import json
from decimal import Decimal

import requests

from talk2record.ai.providers._legacy_prompts import (
    LEGACY_SALES_EXTRACTION_SYSTEM_PROMPT,
)
from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.base import TranscriptionResult

# Re-exported under the historical name so any external code importing the
# old constant continues to work. New code should pass ``system_prompt`` to
# ``extract()`` instead, resolved from a ``PromptTemplate`` row.
EXTRACTION_SYSTEM_PROMPT = LEGACY_SALES_EXTRACTION_SYSTEM_PROMPT


class OpenAITranscriptionProvider:
    provider_name = "openai"
    model_name = "whisper-1"

    def __init__(
        self,
        api_key: str = "",
        *,
        model: str = "",
        base_url: str = "",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url or ""
        if model:
            self.model_name = model

    def transcribe(
        self,
        *,
        audio_url: str,
        audio_bytes: bytes | None = None,
        context_label: str = "",
    ) -> TranscriptionResult:
        import openai  # noqa: PLC0415 — lazy import to avoid hard dep at startup

        if audio_bytes is None:
            if not audio_url:
                msg = "audio_url is required for OpenAI Whisper transcription"
                raise ValueError(msg)

            response = requests.get(audio_url, timeout=30)
            response.raise_for_status()
            audio_bytes = response.content

        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.ogg"

        client_kwargs: dict = {"api_key": self._api_key or None}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        client = openai.OpenAI(**client_kwargs)
        transcription = client.audio.transcriptions.create(
            model=self.model_name,
            file=audio_file,
        )
        transcript = transcription.text.strip()

        return TranscriptionResult(
            transcript=transcript,
            provider=self.provider_name,
            model=self.model_name,
        )


class OpenAIExtractionProvider:
    provider_name = "openai"
    model_name = "gpt-4o"

    def __init__(
        self,
        api_key: str = "",
        *,
        model: str = "",
        base_url: str = "",
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url or ""
        if model:
            self.model_name = model

    def extract(
        self,
        *,
        transcript: str,
        context: dict,
        prompt_version: str,
        system_prompt: str = "",
        user_prompt: str = "",
    ) -> ExtractionResult:
        import openai  # noqa: PLC0415

        client_kwargs: dict = {"api_key": self._api_key or None}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        client = openai.OpenAI(**client_kwargs)

        resolved_system = system_prompt or LEGACY_SALES_EXTRACTION_SYSTEM_PROMPT
        resolved_user = user_prompt or f"Transcript:\n{transcript}"

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": resolved_system},
                {"role": "user", "content": resolved_user},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

        raw = (response.choices[0].message.content or "{}").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        if not system_prompt:
            # Legacy code-path: preserve the sales-flavored shape callers
            # have always received from this provider.
            data = _apply_legacy_sales_shape(data, transcript=transcript, context=context)

        return ExtractionResult(
            data=data,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.92"),
        )


def _apply_legacy_sales_shape(data: dict, *, transcript: str, context: dict) -> dict:
    """Legacy post-processing that pads missing sales fields with sensible defaults.

    Only invoked when no taxonomy ``system_prompt`` is supplied — i.e. the
    caller is still on the legacy :class:`ExtractionService` pathway.
    """

    data["voice_transcript"] = transcript
    data.setdefault("customer_name", str(context.get("customer_name") or ""))
    data.setdefault("product", str(context.get("product") or ""))
    data.setdefault("quantity", int(context.get("quantity") or 1))
    data.setdefault("amount", float(context.get("amount") or 0.0))
    data.setdefault("currency", str(context.get("currency") or "USD"))
    data.setdefault("payment_method", str(context.get("payment_method") or ""))

    try:
        data["quantity"] = int(data["quantity"])
    except (TypeError, ValueError):
        data["quantity"] = 1
    try:
        data["amount"] = float(data["amount"])
    except (TypeError, ValueError):
        data["amount"] = 0.0

    return data
