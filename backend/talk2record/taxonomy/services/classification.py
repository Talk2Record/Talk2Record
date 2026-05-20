"""Classify a transcript into ``(industry, category)`` pairs with confidence.

Pipeline:

1. Run every enabled :class:`ProcessingRule` against the transcript. Each
   rule contributes a per-``(industry, category)`` weighted score.
2. If the strongest score is above
   :data:`MIN_RULE_CONFIDENCE`, return rule-based scores as the result.
3. Otherwise, optionally call an LLM via the ``classification``
   :class:`PromptTemplate` for a fallback classification. The LLM is only
   invoked when ``allow_llm=True`` and an extraction-capable provider is
   configured.
4. Whatever is returned is normalized so confidences are clamped to
   ``[0.0, 1.0]`` and unknown slugs are dropped.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from dataclasses import field
from decimal import Decimal

from django.conf import settings

from talk2record.ai.models import AITask
from talk2record.ai.providers.mock import MockExtractionProvider
from talk2record.ai.resolver import resolve as resolve_ai
from talk2record.taxonomy.models import Category, Industry, ProcessingRule, RuleType
from talk2record.taxonomy.services.prompt_resolver import PromptResolver

logger = logging.getLogger(__name__)

MIN_RULE_CONFIDENCE = 0.5


@dataclass
class IndustryScore:
    slug: str
    confidence: float

    def to_dict(self) -> dict:
        return {"slug": self.slug, "confidence": round(self.confidence, 4)}


@dataclass
class CategoryScore:
    industry: str
    slug: str
    confidence: float

    def to_dict(self) -> dict:
        return {
            "industry": self.industry,
            "slug": self.slug,
            "confidence": round(self.confidence, 4),
        }


@dataclass
class ClassificationResult:
    industries: list[IndustryScore] = field(default_factory=list)
    categories: list[CategoryScore] = field(default_factory=list)
    source: str = "rules"  # "rules" | "llm" | "rules+llm" | "none"
    raw_llm_response: str = ""

    @property
    def top_confidence(self) -> float:
        if self.categories:
            return max(c.confidence for c in self.categories)
        if self.industries:
            return max(i.confidence for i in self.industries)
        return 0.0


class ClassificationService:
    @classmethod
    def classify(
        cls,
        transcript: str,
        *,
        allow_llm: bool = True,
        min_confidence: float | None = None,
    ) -> ClassificationResult:
        if not transcript:
            return ClassificationResult(source="none")

        threshold = (
            min_confidence
            if min_confidence is not None
            else getattr(settings, "TAXONOMY_CLASSIFICATION_MIN_CONFIDENCE", MIN_RULE_CONFIDENCE)
        )

        rule_result = cls._classify_with_rules(transcript)
        if rule_result.top_confidence >= threshold:
            return rule_result

        if not allow_llm:
            return rule_result

        llm_result = cls._classify_with_llm(transcript)
        if llm_result is None:
            return rule_result

        return cls._merge(rule_result, llm_result)

    # ------------------------------------------------------------------
    # Rule engine
    # ------------------------------------------------------------------

    @classmethod
    def _classify_with_rules(cls, transcript: str) -> ClassificationResult:
        rules = list(
            ProcessingRule.objects.filter(
                enabled=True,
                industry__enabled=True,
            )
            .select_related("industry", "category")
            .order_by("priority"),
        )
        if not rules:
            return ClassificationResult(source="none")

        text = transcript.lower()
        industry_scores: dict[str, float] = {}
        category_scores: dict[tuple[str, str], float] = {}

        for rule in rules:
            score = _score_rule(rule, text)
            if score <= 0:
                continue
            industry_scores[rule.industry.slug] = (
                industry_scores.get(rule.industry.slug, 0.0) + score
            )
            if rule.category_id and rule.category.enabled:
                key = (rule.industry.slug, rule.category.slug)
                category_scores[key] = category_scores.get(key, 0.0) + score

        if not industry_scores and not category_scores:
            return ClassificationResult(source="rules")

        industries = sorted(
            [
                IndustryScore(slug=slug, confidence=min(score, 1.0))
                for slug, score in industry_scores.items()
            ],
            key=lambda i: -i.confidence,
        )
        categories = sorted(
            [
                CategoryScore(
                    industry=industry_slug,
                    slug=category_slug,
                    confidence=min(score, 1.0),
                )
                for (industry_slug, category_slug), score in category_scores.items()
            ],
            key=lambda c: -c.confidence,
        )
        return ClassificationResult(
            industries=industries,
            categories=categories,
            source="rules",
        )

    # ------------------------------------------------------------------
    # LLM fallback
    # ------------------------------------------------------------------

    @classmethod
    def _classify_with_llm(cls, transcript: str) -> ClassificationResult | None:
        catalog = _build_catalog()
        if not catalog["industries"]:
            return None

        resolved = PromptResolver.resolve(
            purpose="classification",
            variables={
                "transcript": transcript,
                "catalog": json.dumps(catalog, indent=2),
            },
        )
        if resolved is None:
            return None

        provider = cls._extraction_provider()
        if provider is None:
            return None

        try:
            result = provider.extract(
                transcript=transcript,
                context={"catalog": catalog},
                prompt_version=resolved.version_label,
                system_prompt=resolved.system_prompt,
                user_prompt=resolved.user_prompt,
            )
        except Exception:  # noqa: BLE001 - LLM failure must not break the pipeline.
            logger.exception("Classification LLM call failed")
            return None

        data = result.data if isinstance(result.data, dict) else {}
        raw_payload = json.dumps(data) if data else ""
        return _parse_llm_payload(data, raw_payload)

    @classmethod
    def _extraction_provider(cls):
        resolution = resolve_ai(task=AITask.EXTRACTION)
        if resolution is None or resolution.spec.chat_factory is None:
            return MockExtractionProvider()
        if resolution.provider_slug != "mock" and not resolution.api_key:
            return MockExtractionProvider()
        try:
            return resolution.build_chat_provider()
        except Exception:  # noqa: BLE001 - same as above.
            logger.exception("Could not build chat provider for classification")
            return None

    # ------------------------------------------------------------------
    # Merging
    # ------------------------------------------------------------------

    @classmethod
    def _merge(
        cls,
        rules: ClassificationResult,
        llm: ClassificationResult,
    ) -> ClassificationResult:
        combined_industries: dict[str, float] = {
            i.slug: i.confidence for i in rules.industries
        }
        for i in llm.industries:
            combined_industries[i.slug] = max(
                combined_industries.get(i.slug, 0.0),
                i.confidence,
            )

        combined_categories: dict[tuple[str, str], float] = {
            (c.industry, c.slug): c.confidence for c in rules.categories
        }
        for c in llm.categories:
            combined_categories[(c.industry, c.slug)] = max(
                combined_categories.get((c.industry, c.slug), 0.0),
                c.confidence,
            )

        return ClassificationResult(
            industries=sorted(
                [
                    IndustryScore(slug=slug, confidence=confidence)
                    for slug, confidence in combined_industries.items()
                ],
                key=lambda i: -i.confidence,
            ),
            categories=sorted(
                [
                    CategoryScore(industry=ind, slug=cat, confidence=confidence)
                    for (ind, cat), confidence in combined_categories.items()
                ],
                key=lambda c: -c.confidence,
            ),
            source="rules+llm",
            raw_llm_response=llm.raw_llm_response,
        )


def _score_rule(rule: ProcessingRule, text: str) -> float:
    config = rule.rule_config or {}
    weight = float(config.get("weight", 0.3))

    if rule.rule_type == RuleType.KEYWORD_MATCH:
        keywords = [str(k).lower() for k in config.get("keywords", [])]
        hits = sum(1 for kw in keywords if kw and kw in text)
        if hits == 0:
            return 0.0
        # Diminishing returns: log-ish growth so a single hit isn't max.
        return min(1.0, weight * (0.6 + 0.2 * hits))

    if rule.rule_type == RuleType.REGEX_MATCH:
        pattern = config.get("pattern")
        if not pattern:
            return 0.0
        try:
            if re.search(pattern, text, flags=re.IGNORECASE):
                return min(1.0, weight)
        except re.error:
            return 0.0
        return 0.0

    if rule.rule_type == RuleType.PHRASE_SCORE:
        phrases = [str(p).lower() for p in config.get("phrases", [])]
        hits = sum(1 for ph in phrases if ph and ph in text)
        if hits == 0:
            return 0.0
        return min(1.0, weight * (0.7 + 0.15 * hits))

    return 0.0


def _build_catalog() -> dict:
    industries = []
    categories = []
    for industry in Industry.objects.filter(enabled=True).order_by("priority", "slug"):
        industries.append(
            {
                "slug": industry.slug,
                "name": industry.name,
                "description": industry.description,
            },
        )
        for category in Category.objects.filter(
            industry=industry,
            enabled=True,
        ).order_by("priority", "slug"):
            categories.append(
                {
                    "industry": industry.slug,
                    "slug": category.slug,
                    "name": category.name,
                    "description": category.description,
                },
            )
    return {"industries": industries, "categories": categories}


def _parse_llm_payload(data: dict, raw: str) -> ClassificationResult:
    industries = []
    categories = []
    for item in data.get("industries", []) or []:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "").strip()
        if not slug:
            continue
        industries.append(
            IndustryScore(
                slug=slug,
                confidence=_clamp_confidence(item.get("confidence")),
            ),
        )
    for item in data.get("categories", []) or []:
        if not isinstance(item, dict):
            continue
        industry_slug = str(item.get("industry") or "").strip()
        slug = str(item.get("slug") or "").strip()
        if not slug or not industry_slug:
            continue
        categories.append(
            CategoryScore(
                industry=industry_slug,
                slug=slug,
                confidence=_clamp_confidence(item.get("confidence")),
            ),
        )
    return ClassificationResult(
        industries=industries,
        categories=categories,
        source="llm",
        raw_llm_response=raw,
    )


def _clamp_confidence(value: object) -> float:
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            f = float(Decimal(str(value)))
        except Exception:  # noqa: BLE001
            return 0.0
    return max(0.0, min(1.0, f))
