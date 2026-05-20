"""Dynamic, admin-managed taxonomy for the AI extraction platform.

Six models — Industry, Category, ExtractionSchema, PromptTemplate,
DomainDictionary, ProcessingRule — together describe *what* the platform can
extract, *how* it should extract it, and *which vocabulary* it should
normalize against. Every row is editable in Django admin; no important fact
about a domain should live in Python.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _


class TimestampedModel(models.Model):
    """Abstract base that supplies created_at / updated_at columns."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Industry(TimestampedModel):
    """Top-level business domain (construction, logistics, sales, ...)."""

    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text=_("Lower numbers are evaluated first."),
    )

    class Meta:
        verbose_name = _("Industry")
        verbose_name_plural = _("Industries")
        ordering = ["priority", "name"]
        indexes = [
            models.Index(fields=["enabled", "priority"], name="industry_active_idx"),
        ]

    def __str__(self) -> str:
        return self.name


class Category(TimestampedModel):
    """Sub-type inside an :class:`Industry` (e.g. construction.material_delivery)."""

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="categories",
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=64)
    description = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text=_("Lower numbers are evaluated first."),
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["industry__priority", "priority", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["industry", "slug"],
                name="unique_category_slug_per_industry",
            ),
        ]
        indexes = [
            models.Index(
                fields=["industry", "enabled", "priority"],
                name="category_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.industry.slug}.{self.slug}"

    @property
    def full_slug(self) -> str:
        return f"{self.industry.slug}.{self.slug}"


class ExtractionSchema(TimestampedModel):
    """Versioned JSON Schema that describes the expected extraction payload."""

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="schemas",
    )
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    json_schema = models.JSONField(
        default=dict,
        help_text=_("JSON Schema (draft-07) describing the extraction payload."),
    )
    required_fields = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Optional convenience list mirroring schema['required']."),
    )
    enabled = models.BooleanField(default=True)
    is_default = models.BooleanField(
        default=False,
        help_text=_("Default schema for this category. Exactly one allowed."),
    )

    class Meta:
        verbose_name = _("Extraction schema")
        verbose_name_plural = _("Extraction schemas")
        ordering = ["category", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["category", "name", "version"],
                name="unique_schema_version",
            ),
            models.UniqueConstraint(
                fields=["category"],
                condition=models.Q(is_default=True),
                name="one_default_schema_per_category",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "enabled"], name="schema_active_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.category}::{self.name}@v{self.version}"

    def clean(self) -> None:
        super().clean()
        if not isinstance(self.json_schema, dict):
            raise ValidationError(
                {"json_schema": _("Must be a JSON object (dict).")},
            )
        if not isinstance(self.required_fields, list):
            raise ValidationError(
                {"required_fields": _("Must be a JSON list.")},
            )


class PromptPurpose(models.TextChoices):
    """What pipeline step a :class:`PromptTemplate` is meant for."""

    CLASSIFICATION = "classification", _("Classification")
    EXTRACTION = "extraction", _("Extraction")
    NORMALIZATION = "normalization", _("Normalization")
    VALIDATION = "validation", _("Validation")
    REVIEW = "review", _("Review")


class PromptTemplate(TimestampedModel):
    """Versioned, admin-managed prompt.

    Resolution order (most-specific first):

    1. ``(industry, category, purpose)``
    2. ``(industry, null, purpose)``
    3. ``(null, null, purpose)``

    Within a tier, the row with the highest ``version`` and ``enabled=True``
    wins. ``version`` is bumped via the admin (never mutated in place) so
    historical records can be replayed against the exact prompt that
    produced them.
    """

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="prompts",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="prompts",
        null=True,
        blank=True,
    )
    purpose = models.CharField(
        max_length=32,
        choices=PromptPurpose.choices,
    )
    title = models.CharField(max_length=160)
    version = models.PositiveIntegerField(default=1)
    system_prompt = models.TextField(
        help_text=_(
            "System prompt. Supports {transcript}, {schema}, {dictionary}, "
            "{industry}, {category} placeholders.",
        ),
    )
    user_prompt = models.TextField(
        blank=True,
        help_text=_("Optional user prompt template. Same placeholders as system_prompt."),
    )
    example_input = models.TextField(blank=True)
    example_output = models.TextField(blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Prompt template")
        verbose_name_plural = _("Prompt templates")
        ordering = ["purpose", "industry", "category", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["industry", "category", "purpose", "version"],
                name="unique_taxonomy_prompt_version",
            ),
        ]
        indexes = [
            models.Index(
                fields=["purpose", "enabled", "industry", "category"],
                name="prompt_lookup_idx",
            ),
        ]

    def __str__(self) -> str:
        scope = self._scope_label()
        return f"{scope}/{self.purpose} v{self.version}"

    def clean(self) -> None:
        super().clean()
        if self.category and self.industry and self.category.industry_id != self.industry_id:
            raise ValidationError(
                {
                    "category": _(
                        "Category must belong to the selected industry.",
                    ),
                },
            )
        if self.category and not self.industry:
            self.industry = self.category.industry

    def _scope_label(self) -> str:
        if self.category_id:
            return str(self.category)
        if self.industry_id:
            return self.industry.slug
        return "global"


class DomainDictionary(TimestampedModel):
    """Term / abbreviation normalization entry.

    Scoping rules:

    * ``industry`` + ``category`` set -> applies only to that category.
    * ``industry`` set, ``category`` null -> applies to all categories in
      that industry.
    * Both null -> global.

    Lookups apply the narrowest scope first; longer terms match before
    shorter terms so ``m3`` is never destroyed by an ``m -> meter`` rule.
    """

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="dictionary_entries",
        null=True,
        blank=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="dictionary_entries",
        null=True,
        blank=True,
    )
    term = models.CharField(max_length=120)
    normalized_term = models.CharField(max_length=240)
    description = models.CharField(max_length=255, blank=True)
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Domain dictionary entry")
        verbose_name_plural = _("Domain dictionary entries")
        ordering = ["industry__priority", "category__priority", "term"]
        constraints = [
            models.UniqueConstraint(
                fields=["industry", "category", "term"],
                name="unique_dictionary_term_per_scope",
            ),
        ]
        indexes = [
            models.Index(
                fields=["industry", "category", "enabled"],
                name="dictionary_scope_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.term} -> {self.normalized_term}"

    def clean(self) -> None:
        super().clean()
        if self.category and self.industry and self.category.industry_id != self.industry_id:
            raise ValidationError(
                {
                    "category": _(
                        "Category must belong to the selected industry.",
                    ),
                },
            )
        if self.category and not self.industry:
            self.industry = self.category.industry


class RuleType(models.TextChoices):
    """Deterministic classification rule kinds."""

    KEYWORD_MATCH = "keyword_match", _("Keyword match")
    REGEX_MATCH = "regex_match", _("Regex match")
    PHRASE_SCORE = "phrase_score", _("Phrase score")


class ProcessingRule(TimestampedModel):
    """Cheap deterministic classifier that runs before any LLM call.

    Used by :class:`ClassificationService` to score industries and
    categories from the transcript. Falls back to an LLM-based
    classification prompt when no rule scores above the threshold.

    ``rule_config`` payloads:

    * ``keyword_match``: ``{"keywords": ["cement", "sand"], "weight": 0.4}``
    * ``regex_match``: ``{"pattern": "(\\b\\d+\\s*bags?\\b)", "weight": 0.3}``
    * ``phrase_score``: ``{"phrases": ["paid the fundi"], "weight": 0.5}``
    """

    industry = models.ForeignKey(
        Industry,
        on_delete=models.CASCADE,
        related_name="processing_rules",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="processing_rules",
        null=True,
        blank=True,
    )
    rule_type = models.CharField(
        max_length=32,
        choices=RuleType.choices,
        default=RuleType.KEYWORD_MATCH,
    )
    rule_config = models.JSONField(default=dict, blank=True)
    priority = models.PositiveSmallIntegerField(
        default=100,
        help_text=_("Lower numbers are evaluated first."),
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Processing rule")
        verbose_name_plural = _("Processing rules")
        ordering = ["industry__priority", "priority", "category__priority"]
        indexes = [
            models.Index(
                fields=["industry", "category", "enabled", "priority"],
                name="rule_lookup_idx",
            ),
        ]

    def __str__(self) -> str:
        scope = str(self.category) if self.category_id else self.industry.slug
        return f"{scope}::{self.rule_type}"

    def clean(self) -> None:
        super().clean()
        if self.category and self.category.industry_id != self.industry_id:
            raise ValidationError(
                {
                    "category": _(
                        "Category must belong to the selected industry.",
                    ),
                },
            )
        if not isinstance(self.rule_config, dict):
            raise ValidationError(
                {"rule_config": _("Must be a JSON object (dict).")},
            )
