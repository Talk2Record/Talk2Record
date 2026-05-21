from __future__ import annotations

import io
import json
from decimal import Decimal

import requests

from talk2record.ai.providers.base import (
    DEFAULT_EXTRACTION_SYSTEM_PROMPT,
    ExtractionResult,
    TranscriptionResult,
)


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

        resolved_system = system_prompt or DEFAULT_EXTRACTION_SYSTEM_PROMPT
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

        return ExtractionResult(
            data=data,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.92"),
        )
