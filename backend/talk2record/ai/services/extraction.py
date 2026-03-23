from __future__ import annotations

from django.conf import settings

from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.mock import MockExtractionProvider
from talk2record.ai.services.prompts import PromptTemplateService
from talk2record.ai.validation.schemas import validate_extraction_payload
from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret


class ExtractionService:
    _providers: dict[str, object] = {
        "mock": MockExtractionProvider(),
    }

    @classmethod
    def _provider(cls):
        integration = get_active_integration("ai")
        configured = ""
        if integration is not None:
            configured = str(
                integration.config.get("extraction_provider")
                or integration.config.get("provider")
                or "",
            ).strip()
            get_active_integration_secret("ai")
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
