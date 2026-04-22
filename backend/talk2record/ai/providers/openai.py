from __future__ import annotations

import io
import json
from decimal import Decimal

import requests

from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.base import TranscriptionResult

EXTRACTION_SYSTEM_PROMPT = """\
You are a data extraction assistant for a business sales recording system.
Given a voice note transcript, extract structured fields and return ONLY valid JSON with no
markdown, code fences, or explanation.

Fields to extract:
- customer_name: string (person or company placing the order; empty string if unknown)
- product: string (item or service ordered; empty string if unclear)
- quantity: integer (number of units; default 1 if not mentioned)
- amount: decimal number (total amount paid or owed; 0 if not mentioned)
- currency: 3-letter ISO code (e.g. USD, KES, GBP, NGN; default "USD")
- payment_method: string (e.g. "cash", "mpesa", "card", "bank_transfer"; empty string if unknown)
- voice_transcript: string (the original transcript verbatim)

Return exactly this JSON shape with no extra keys:
{"customer_name": "...", "product": "...", "quantity": 1, "amount": 0.00,
 "currency": "USD", "payment_method": "...", "voice_transcript": "..."}
"""


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
        context_label: str = "",
    ) -> TranscriptionResult:
        import openai  # noqa: PLC0415 — lazy import to avoid hard dep at startup

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
    ) -> ExtractionResult:
        import openai  # noqa: PLC0415

        client_kwargs: dict = {"api_key": self._api_key or None}
        if self._base_url:
            client_kwargs["base_url"] = self._base_url
        client = openai.OpenAI(**client_kwargs)

        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": f"Transcript:\n{transcript}"},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )

        raw = (response.choices[0].message.content or "{}").strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

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

        return ExtractionResult(
            data=data,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.92"),
        )
