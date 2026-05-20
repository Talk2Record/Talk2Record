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
    provider_name = "mock"
    model_name = "mock-extractor-v1"

    def extract(
        self,
        *,
        transcript: str,
        context: dict,
        prompt_version: str,
    ) -> ExtractionResult:
        customer_name = str(context.get("customer_name") or "Unknown customer")
        product = str(context.get("product") or "WhatsApp voice note")
        amount = Decimal(str(context.get("amount") or "0.00"))
        quantity = int(context.get("quantity") or 1)
        currency = str(context.get("currency") or "USD")
        payment_method = str(context.get("payment_method") or "")
        confidence_score = Decimal("0.950")
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
            confidence_score=confidence_score,
        )
