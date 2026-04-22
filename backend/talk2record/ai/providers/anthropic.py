from __future__ import annotations

import json
import re
from decimal import Decimal

from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.openai import EXTRACTION_SYSTEM_PROMPT


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
    ) -> ExtractionResult:
        import anthropic  # noqa: PLC0415 — lazy import to avoid hard dep at startup

        client = anthropic.Anthropic(api_key=self._api_key or None)

        message = client.messages.create(
            model=self.model_name,
            max_tokens=1024,
            system=EXTRACTION_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": f"Transcript:\n{transcript}"},
            ],
        )

        raw = (message.content[0].text if message.content else "{}").strip()
        raw = _strip_markdown_fences(raw)

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
            confidence_score=Decimal("0.93"),
        )
