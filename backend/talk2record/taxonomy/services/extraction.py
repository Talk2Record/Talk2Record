"""Run schema-driven, prompt-driven extraction against a transcript.

The service resolves the extraction prompt and schema for a given
``Category`` via the database, calls the active AI provider with the
resolved prompt, and returns the model's structured output. The caller
(usually :class:`ExtractionPipeline`) is responsible for persisting the
result and running validation afterwards.

Production ingestion uses this service via
:class:`~talk2record.taxonomy.services.orchestrator.ExtractionPipeline`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from talk2record.ai.models import AITask
from talk2record.ai.providers.mock import MockExtractionProvider
from talk2record.ai.resolver import resolve as resolve_ai
from talk2record.taxonomy.models import Category, ExtractionSchema
from talk2record.taxonomy.services.prompt_resolver import PromptResolver, ResolvedPrompt

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from talk2record.ai.providers.base import ExtractionResult


@dataclass(frozen=True)
class DynamicExtractionResult:
    data: dict
    provider: str
    model: str
    prompt_version: str
    schema_version: str
    confidence_score: float
    prompt: ResolvedPrompt | None


class DynamicExtractionService:
    @classmethod
    def extract(
        cls,
        *,
        transcript: str,
        category: Category,
        normalized_transcript: str = "",
        dictionary_applied: list[dict] | None = None,
    ) -> DynamicExtractionResult:
        schema = cls._resolve_schema(category)
        prompt = cls._resolve_prompt(
            category=category,
            transcript=transcript,
            normalized_transcript=normalized_transcript,
            schema=schema,
            dictionary_applied=dictionary_applied or [],
        )
        provider = cls._provider()
        try:
            result = provider.extract(
                transcript=normalized_transcript or transcript,
                context={
                    "industry": category.industry.slug,
                    "category": category.slug,
                    "schema": schema.json_schema if schema else {},
                    "dictionary_applied": dictionary_applied or [],
                },
                prompt_version=prompt.version_label if prompt else "v0",
                system_prompt=prompt.system_prompt if prompt else "",
                user_prompt=prompt.user_prompt if prompt else "",
            )
        except Exception:  # noqa: BLE001 - any provider failure → mock fallback.
            logger.exception(
                "Extraction provider %s failed; falling back to mock",
                getattr(provider, "provider_name", "unknown"),
            )
            provider = MockExtractionProvider()
            result = provider.extract(
                transcript=normalized_transcript or transcript,
                context={
                    "industry": category.industry.slug,
                    "category": category.slug,
                },
                prompt_version=prompt.version_label if prompt else "v0",
                system_prompt=prompt.system_prompt if prompt else "",
                user_prompt=prompt.user_prompt if prompt else "",
            )
        return _build_result(result, prompt=prompt, schema=schema)

    # ------------------------------------------------------------------

    @classmethod
    def _provider(cls):
        resolution = resolve_ai(task=AITask.EXTRACTION)
        if resolution is None or resolution.spec.chat_factory is None:
            return MockExtractionProvider()
        if resolution.provider_slug != "mock" and not resolution.api_key:
            # Active provider has no credentials configured — degrade to
            # mock rather than letting the SDK raise during ``__init__``.
            logger.warning(
                "Active AI provider %r has no API key; using mock extraction.",
                resolution.provider_slug,
            )
            return MockExtractionProvider()
        try:
            return resolution.build_chat_provider()
        except Exception:  # noqa: BLE001 — fall back to mock if construction fails.
            logger.exception(
                "Could not build chat provider %r; using mock extraction.",
                resolution.provider_slug,
            )
            return MockExtractionProvider()

    @classmethod
    def _resolve_schema(cls, category: Category) -> ExtractionSchema | None:
        return (
            ExtractionSchema.objects.filter(category=category, enabled=True)
            .order_by("-is_default", "-version")
            .first()
        )

    @classmethod
    def _resolve_prompt(
        cls,
        *,
        category: Category,
        transcript: str,
        normalized_transcript: str,
        schema: ExtractionSchema | None,
        dictionary_applied: list[dict],
    ) -> ResolvedPrompt | None:
        return PromptResolver.resolve(
            purpose="extraction",
            industry=category.industry,
            category=category,
            variables={
                "transcript": normalized_transcript or transcript,
                "schema": json.dumps(schema.json_schema, indent=2) if schema else "{}",
                "dictionary": _format_dictionary(dictionary_applied),
            },
        )


def _format_dictionary(applied: list[dict]) -> str:
    if not applied:
        return "(no normalization applied)"
    return "\n".join(
        f"- {entry['term']} -> {entry['normalized_term']}"
        for entry in applied
    )


def _build_result(
    raw: ExtractionResult,
    *,
    prompt: ResolvedPrompt | None,
    schema: ExtractionSchema | None,
) -> DynamicExtractionResult:
    confidence = float(raw.confidence_score or 0)
    if prompt is None or schema is None:
        # No prompt or schema means we cannot trust the structure beyond a
        # raw transcript echo; reduce reported confidence accordingly.
        confidence = min(confidence, 0.3)

    return DynamicExtractionResult(
        data=dict(raw.data or {}),
        provider=raw.provider,
        model=raw.model,
        prompt_version=raw.prompt_version,
        schema_version=f"v{schema.version}" if schema else "",
        confidence_score=confidence,
        prompt=prompt,
    )
