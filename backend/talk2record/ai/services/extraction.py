from __future__ import annotations

from django.conf import settings

from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.mock import MockExtractionProvider
from talk2record.ai.services.prompts import PromptTemplateService
from talk2record.ai.validation.schemas import validate_extraction_payload
from talk2record.ai.runtime import get_active_ai_settings
from talk2record.ai.runtime import get_ai_credential_plaintext


class ExtractionService:
    _providers: dict[str, object] = {
        "mock": MockExtractionProvider(),
    }

    @classmethod
    def _provider(cls):
        settings_row = get_active_ai_settings()
        configured = ""
        if settings_row is not None:
            cfg = settings_row.config if isinstance(settings_row.config, dict) else {}
            configured = str(
                cfg.get("extraction_provider")
                or cfg.get("provider")
                or "",
            ).strip()
            get_ai_credential_plaintext()
        if not configured:
            configured = getattr(settings, "AI_EXTRACTION_PROVIDER", "mock")
        return cls._providers.get(configured, cls._providers["mock"])

    @classmethod
    def extract(
        cls,
        *,
        transcript: str,
        context: dict | None = None,
    ) -> ExtractionResult:
        provider = cls._provider()
        prompt_version = PromptTemplateService.resolve_extraction_prompt_version(
            provider=provider.provider_name,
            model=provider.model_name,
        )
        result = provider.extract(
            transcript=transcript,
            context=context or {},
            prompt_version=prompt_version,
        )
        validated_payload = validate_extraction_payload(result.data)
        return ExtractionResult(
            data=validated_payload,
            provider=result.provider,
            model=result.model,
            prompt_version=result.prompt_version,
            confidence_score=result.confidence_score,
        )
