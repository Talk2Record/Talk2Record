"""End-to-end seed-data tests: re-running the seed must be idempotent and
must always leave the construction industry fully provisioned."""

from __future__ import annotations

import pytest
from django.core.management import call_command

from talk2record.taxonomy.models import (
    Category,
    DomainDictionary,
    ExtractionSchema,
    Industry,
    ProcessingRule,
    PromptTemplate,
)


@pytest.mark.django_db
def test_seed_creates_construction_industry():
    call_command("seed_data")

    construction = Industry.objects.get(slug="construction")
    assert construction.enabled is True
    # Five core construction categories must exist.
    categories = set(
        Category.objects.filter(industry=construction).values_list("slug", flat=True),
    )
    assert {
        "material_delivery",
        "labor_payment",
        "site_progress",
        "equipment_use",
        "excavation",
    }.issubset(categories)


@pytest.mark.django_db
def test_seed_creates_default_schemas_for_every_construction_category():
    call_command("seed_data")
    construction = Industry.objects.get(slug="construction")
    for category in Category.objects.filter(industry=construction):
        default_schema = ExtractionSchema.objects.filter(
            category=category, is_default=True,
        ).first()
        assert default_schema is not None, (
            f"No default schema for {category.full_slug}"
        )
        assert isinstance(default_schema.json_schema, dict)


@pytest.mark.django_db
def test_seed_creates_prompts_for_every_construction_category():
    call_command("seed_data")
    construction = Industry.objects.get(slug="construction")
    for category in Category.objects.filter(industry=construction):
        prompt = PromptTemplate.objects.filter(
            industry=construction,
            category=category,
            purpose="extraction",
            enabled=True,
        ).first()
        assert prompt is not None, f"No extraction prompt for {category.full_slug}"
        assert prompt.system_prompt.strip()


@pytest.mark.django_db
def test_seed_creates_global_classification_prompt():
    call_command("seed_data")
    assert PromptTemplate.objects.filter(
        industry__isnull=True,
        category__isnull=True,
        purpose="classification",
        enabled=True,
    ).exists()


@pytest.mark.django_db
def test_seed_creates_dictionary_entries():
    call_command("seed_data")
    construction = Industry.objects.get(slug="construction")
    entries = DomainDictionary.objects.filter(industry=construction, enabled=True)
    assert entries.count() >= 10
    assert entries.filter(term="OPC").exists()
    assert entries.filter(term="fundi").exists()


@pytest.mark.django_db
def test_seed_creates_processing_rules():
    call_command("seed_data")
    construction = Industry.objects.get(slug="construction")
    assert ProcessingRule.objects.filter(industry=construction, enabled=True).count() >= 5


@pytest.mark.django_db
def test_seed_is_idempotent():
    call_command("seed_data")
    counts_first = _taxonomy_counts()
    call_command("seed_data")
    counts_second = _taxonomy_counts()
    assert counts_first == counts_second, (
        f"Seed not idempotent: {counts_first} -> {counts_second}"
    )


@pytest.mark.django_db
def test_seed_creates_empty_shell_industries():
    """Industries other than construction ship as enabled shells."""

    call_command("seed_data")
    for slug in ("logistics", "sales", "healthcare", "agriculture", "field_operations", "support"):
        industry = Industry.objects.get(slug=slug)
        # No categories yet — those are added via the admin per customer.
        assert Category.objects.filter(industry=industry).count() == 0


def _taxonomy_counts() -> dict[str, int]:
    return {
        "industries": Industry.objects.count(),
        "categories": Category.objects.count(),
        "schemas": ExtractionSchema.objects.count(),
        "prompts": PromptTemplate.objects.count(),
        "dictionary": DomainDictionary.objects.count(),
        "rules": ProcessingRule.objects.count(),
    }
