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
    """In-memory extraction provider for tests and offline development.

    Behaviour:

    * When ``system_prompt`` is provided (taxonomy pipeline), echo the
      transcript and any ``context`` fields back as ``extracted_data``. This
      keeps the mock useful for end-to-end taxonomy tests without needing a
      real LLM.
    * When ``system_prompt`` is empty (legacy sales pipeline), return the
      historical sales-flavored shape that older tests depend on.
    """

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
        if system_prompt:
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

        customer_name = str(context.get("customer_name") or "Unknown customer")
        product = str(context.get("product") or "WhatsApp voice note")
        amount = Decimal(str(context.get("amount") or "0.00"))
        quantity = int(context.get("quantity") or 1)
        currency = str(context.get("currency") or "USD")
        payment_method = str(context.get("payment_method") or "")
        return ExtractionResult(
            data={
                "customer_name": customer_name,
                "product": product,
                "quantity": quantity,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "voice_transcript": transcript,
            },
            provider=self.provider_name,
            model=self.model_name,
            prompt_version=prompt_version,
            confidence_score=Decimal("0.950"),
        )
