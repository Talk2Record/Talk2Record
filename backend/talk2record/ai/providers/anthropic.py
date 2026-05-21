from __future__ import annotations

import json
import re
from decimal import Decimal

from talk2record.ai.providers.base import (
    DEFAULT_EXTRACTION_SYSTEM_PROMPT,
    ExtractionResult,
)


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` fences if the model wraps its output."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


class AnthropicExtractionProvider:
    provider_name = "anthropic"
    model_name = "claude-3-5-sonnet-20241022"

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
        import anthropic  # noqa: PLC0415 — lazy import to avoid hard dep at startup

        client = anthropic.Anthropic(api_key=self._api_key or None)

        resolved_system = system_prompt or DEFAULT_EXTRACTION_SYSTEM_PROMPT
        resolved_user = user_prompt or f"Transcript:\n{transcript}"

        message = client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=resolved_system,
            messages=[
                {"role": "user", "content": resolved_user},
            ],
        )

        raw = (message.content[0].text if message.content else "{}").strip()
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
            confidence_score=Decimal("0.93"),
        )
