from __future__ import annotations

from typing import TYPE_CHECKING

from talk2record.ai.models import AITask
from talk2record.ai.providers.base import ExtractionResult
from talk2record.ai.providers.mock import MockExtractionProvider
from talk2record.ai.resolver import resolve
from talk2record.ai.services.prompts import PromptTemplateService
from talk2record.ai.validation.schemas import validate_extraction_payload

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


class ExtractionService:
    @classmethod
    def _provider(cls, organization: Organization | None = None):
        resolution = resolve(task=AITask.EXTRACTION, organization=organization)
        if resolution is None or resolution.spec.chat_factory is None:
            return MockExtractionProvider()
        return resolution.build_chat_provider()

    @classmethod
    def extract(
        cls,
        *,
        transcript: str,
        context: dict | None = None,
        organization: Organization | None = None,
    ) -> ExtractionResult:
        provider = cls._provider(organization=organization)
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
