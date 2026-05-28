"""Top-level extraction pipeline.

Given a ``Record`` whose transcript artifact already exists, this
orchestrator runs:

1. :class:`ClassificationService` → industries + categories + confidence.
2. :class:`DictionaryNormalizer` → rewrite transcript via the domain dict.
3. :class:`DynamicExtractionService` → per-category prompt+schema-driven
   extraction. Multiple categories may be extracted in a single run.
4. :class:`SchemaValidator` → JSON Schema check per category.
5. Aggregate everything into a single :class:`PipelineOutcome` for the
   caller to persist on the ``Record`` (columns + artifacts).
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

from django.conf import settings

from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import Industry
from talk2record.taxonomy.services.classification import ClassificationResult
from talk2record.taxonomy.services.classification import ClassificationService
from talk2record.taxonomy.services.dictionary import DictionaryNormalizer
from talk2record.taxonomy.services.dictionary import NormalizedText
from talk2record.taxonomy.services.extraction import DynamicExtractionResult
from talk2record.taxonomy.services.extraction import DynamicExtractionService
from talk2record.taxonomy.services.validation import SchemaValidator
from talk2record.taxonomy.services.validation import ValidationResult

DEFAULT_REVIEW_CONFIDENCE = 0.6


@dataclass
class CategoryExtraction:
    industry_slug: str
    category_slug: str
    classification_confidence: float
    extraction: DynamicExtractionResult
    validation: ValidationResult

    def to_artifact(self) -> dict:
        return {
            "industry": self.industry_slug,
            "category": self.category_slug,
            "classification_confidence": self.classification_confidence,
            "extraction": {
                "provider": self.extraction.provider,
                "model": self.extraction.model,
                "prompt_version": self.extraction.prompt_version,
                "schema_version": self.extraction.schema_version,
                "confidence": self.extraction.confidence_score,
                "data": self.extraction.data,
            },
            "validation": {
                "ok": self.validation.ok,
                "errors": self.validation.errors,
            },
        }


@dataclass
class PipelineOutcome:
    transcript: str
    normalized_transcript: str
    classification: ClassificationResult
    normalization: NormalizedText
    extractions: list[CategoryExtraction] = field(default_factory=list)
    needs_review: bool = False
    confidence_score: float = 0.0

    @property
    def detected_industries(self) -> list[dict]:
        return [i.to_dict() for i in self.classification.industries]

    @property
    def detected_categories(self) -> list[dict]:
        return [c.to_dict() for c in self.classification.categories]

    @property
    def extracted_data(self) -> dict | list[dict]:
        if not self.extractions:
            return {}
        if len(self.extractions) == 1:
            return self.extractions[0].extraction.data
        return [e.to_artifact() for e in self.extractions]

    @property
    def validation_errors(self) -> list[dict]:
        errors: list[dict] = []
        for extraction in self.extractions:
            for err in extraction.validation.errors:
                errors.append(
                    {
                        "category": extraction.category_slug,
                        **err,
                    },
                )
        return errors


class ExtractionPipeline:
    @classmethod
    def run(
        cls,
        transcript: str,
        *,
        review_confidence: float | None = None,
        max_categories: int = 3,
    ) -> PipelineOutcome:
        threshold = (
            review_confidence
            if review_confidence is not None
            else getattr(
                settings,
                "TAXONOMY_REVIEW_CONFIDENCE",
                DEFAULT_REVIEW_CONFIDENCE,
            )
        )

        classification = ClassificationService.classify(transcript)

        primary_industry = cls._primary_industry(classification)
        normalization = DictionaryNormalizer.normalize(
            transcript,
            industry=primary_industry,
        )

        categories = cls._select_categories(
            classification,
            max_categories=max_categories,
        )
        extractions = cls._extract_per_category(
            categories=categories,
            classification=classification,
            transcript=transcript,
            normalized=normalization,
        )

        confidence = cls._aggregate_confidence(classification, extractions)
        needs_review = (
            not categories
            or confidence < threshold
            or any(not e.validation.ok for e in extractions)
        )

        return PipelineOutcome(
            transcript=transcript,
            normalized_transcript=normalization.text,
            classification=classification,
            normalization=normalization,
            extractions=extractions,
            needs_review=needs_review,
            confidence_score=confidence,
        )

    # ------------------------------------------------------------------

    @classmethod
    def _primary_industry(cls, classification: ClassificationResult) -> Industry | None:
        if not classification.industries:
            return None
        top = classification.industries[0]
        return Industry.objects.filter(slug=top.slug, enabled=True).first()

    @classmethod
    def _select_categories(
        cls,
        classification: ClassificationResult,
        *,
        max_categories: int,
    ) -> list[tuple[Category, float]]:
        if not classification.categories:
            return []
        selected: list[tuple[Category, float]] = []
        seen_keys: set[tuple[str, str]] = set()
        for score in classification.categories[:max_categories]:
            key = (score.industry, score.slug)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            category = (
                Category.objects.filter(
                    industry__slug=score.industry,
                    slug=score.slug,
                    enabled=True,
                )
                .select_related("industry")
                .first()
            )
            if category is None:
                continue
            selected.append((category, score.confidence))
        return selected

    @classmethod
    def _extract_per_category(
        cls,
        *,
        categories: list[tuple[Category, float]],
        classification: ClassificationResult,
        transcript: str,
        normalized: NormalizedText,
    ) -> list[CategoryExtraction]:
        out: list[CategoryExtraction] = []
        for category, classification_confidence in categories:
            extraction = DynamicExtractionService.extract(
                transcript=transcript,
                category=category,
                normalized_transcript=normalized.text,
                dictionary_applied=normalized.applied,
            )
            schema = (
                category.schemas.filter(enabled=True)
                .order_by("-is_default", "-version")
                .first()
            )
            if schema is not None:
                validation = SchemaValidator.validate(extraction.data, schema=schema)
            else:
                validation = ValidationResult(ok=True)
            out.append(
                CategoryExtraction(
                    industry_slug=category.industry.slug,
                    category_slug=category.slug,
                    classification_confidence=classification_confidence,
                    extraction=extraction,
                    validation=validation,
                ),
            )
        del classification  # currently unused but kept in signature for clarity
        return out

    @classmethod
    def _aggregate_confidence(
        cls,
        classification: ClassificationResult,
        extractions: list[CategoryExtraction],
    ) -> float:
        if not extractions:
            return classification.top_confidence
        components = [classification.top_confidence] + [
            e.extraction.confidence_score for e in extractions
        ]
        return sum(components) / len(components)
