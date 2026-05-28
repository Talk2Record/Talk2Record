"""Thin wrapper around OpenAI-compatible chat APIs (OpenRouter, Groq, ...).

Many providers speak the ``/v1/chat/completions`` protocol that OpenAI's
Python client supports. This adapter lets us plug any of them into the
platform by specifying a ``base_url``, an ``api_key`` and a ``model``.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal

from talk2record.ai.providers.base import DEFAULT_EXTRACTION_SYSTEM_PROMPT
from talk2record.ai.providers.base import ExtractionResult


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


class OpenAICompatibleExtractionProvider:
    """Extraction provider backed by any OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        *,
        provider_name: str,
        api_key: str,
        model: str,
        base_url: str,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model
        self._api_key = api_key
        self._base_url = base_url

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

        client = openai.OpenAI(
            api_key=self._api_key or None,
            base_url=self._base_url or None,
        )

        resolved_system = system_prompt or DEFAULT_EXTRACTION_SYSTEM_PROMPT
        resolved_user = user_prompt or f"Transcript:\n{transcript}"

        kwargs: dict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": resolved_system},
                {"role": "user", "content": resolved_user},
            ],
            "temperature": 0,
        }
        # Not every OpenAI-compatible provider honours response_format.
        # Attempt it first then fall back on failure.
        try:
            response = client.chat.completions.create(
                response_format={"type": "json_object"},
                **kwargs,
            )
        except Exception:  # noqa: BLE001 — fall back to plain JSON prompting.
            response = client.chat.completions.create(**kwargs)

        raw = (response.choices[0].message.content or "{}").strip()
        raw = _strip_markdown_fences(raw)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}

        return ExtractionResult(
            data=data,
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.9"),
        )
