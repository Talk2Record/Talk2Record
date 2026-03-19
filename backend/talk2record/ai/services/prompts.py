from __future__ import annotations

from django.conf import settings

from talk2record.ai.models import AIPromptTemplate


class PromptTemplateService:
    DEFAULT_PROMPT_NAME = "record_extraction"

    @classmethod
    def resolve_extraction_prompt_version(cls, *, provider: str, model: str) -> str:
        template = (
            AIPromptTemplate.objects.filter(
                name=cls.DEFAULT_PROMPT_NAME,
                provider=provider,
                model=model,
            )
            .order_by("-version")
            .first()
        )
        if template is not None:
            return f"v{template.version}"
        return getattr(settings, "AI_EXTRACTION_PROMPT_VERSION", "v1")
