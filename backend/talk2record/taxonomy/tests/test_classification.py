from __future__ import annotations

import pytest

from talk2record.taxonomy.models import ProcessingRule
from talk2record.taxonomy.models import RuleType
from talk2record.taxonomy.services.classification import ClassificationService


@pytest.mark.django_db
def test_keyword_rule_classifies_material_delivery(
    material_delivery_rule,
):
    result = ClassificationService.classify(
        "Delivered 20 bags of cement to site A",
        allow_llm=False,
    )
    assert any(c.slug == "material_delivery" for c in result.categories)
    assert result.top_confidence > 0.5
    assert result.source == "rules"


@pytest.mark.django_db
def test_keyword_rule_classifies_labor_payment(
    labor_payment_rule,
):
    result = ClassificationService.classify(
        "Paid the fundi 2000 cash for slab casting",
        allow_llm=False,
    )
    assert any(c.slug == "labor_payment" for c in result.categories)
    assert result.top_confidence > 0.5


@pytest.mark.django_db
def test_multiple_categories_detected(
    material_delivery_rule,
    labor_payment_rule,
):
    result = ClassificationService.classify(
        "Delivered 20 bags cement and paid the fundi 2000 cash",
        allow_llm=False,
    )
    slugs = {c.slug for c in result.categories}
    assert "material_delivery" in slugs
    assert "labor_payment" in slugs


@pytest.mark.django_db
def test_no_rules_returns_empty_result(db):
    result = ClassificationService.classify("Random text", allow_llm=False)
    assert result.industries == []
    assert result.categories == []


@pytest.mark.django_db
def test_regex_rule_matches(industry, material_delivery_category):
    ProcessingRule.objects.create(
        industry=industry,
        category=material_delivery_category,
        rule_type=RuleType.REGEX_MATCH,
        priority=10,
        rule_config={"pattern": r"\d+\s*bags", "weight": 0.6},
    )
    result = ClassificationService.classify("Got 50 bags today", allow_llm=False)
    assert any(c.slug == "material_delivery" for c in result.categories)


@pytest.mark.django_db
def test_disabled_rules_are_ignored(industry, material_delivery_category):
    ProcessingRule.objects.create(
        industry=industry,
        category=material_delivery_category,
        rule_type=RuleType.KEYWORD_MATCH,
        priority=10,
        rule_config={"keywords": ["cement"], "weight": 0.6},
        enabled=False,
    )
    result = ClassificationService.classify("Delivered cement", allow_llm=False)
    assert result.industries == []


@pytest.mark.django_db
def test_rule_weight_affects_score(industry, material_delivery_category):
    ProcessingRule.objects.create(
        industry=industry,
        category=material_delivery_category,
        rule_type=RuleType.KEYWORD_MATCH,
        priority=10,
        rule_config={"keywords": ["cement"], "weight": 0.1},
    )
    low_weight = ClassificationService.classify("cement", allow_llm=False)
    # With a single keyword and very low weight, confidence should stay low.
    assert low_weight.top_confidence < 0.5
