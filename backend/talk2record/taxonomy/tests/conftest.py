"""Fixtures for taxonomy tests."""

from __future__ import annotations

import pytest

from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import DomainDictionary
from talk2record.taxonomy.models import ExtractionSchema
from talk2record.taxonomy.models import Industry
from talk2record.taxonomy.models import ProcessingRule
from talk2record.taxonomy.models import PromptPurpose
from talk2record.taxonomy.models import PromptTemplate
from talk2record.taxonomy.models import RuleType


@pytest.fixture
def industry(db) -> Industry:
    return Industry.objects.create(
        slug="construction",
        name="Construction",
        priority=10,
    )


@pytest.fixture
def material_delivery_category(industry: Industry) -> Category:
    return Category.objects.create(
        industry=industry,
        slug="material_delivery",
        name="Material delivery",
        priority=10,
    )


@pytest.fixture
def labor_payment_category(industry: Industry) -> Category:
    return Category.objects.create(
        industry=industry,
        slug="labor_payment",
        name="Labor payment",
        priority=20,
    )


@pytest.fixture
def material_delivery_schema(material_delivery_category: Category) -> ExtractionSchema:
    return ExtractionSchema.objects.create(
        category=material_delivery_category,
        name="Material delivery v1",
        version=1,
        is_default=True,
        required_fields=["material"],
        json_schema={
            "type": "object",
            "properties": {
                "material": {"type": "string"},
                "quantity": {"type": "number"},
                "unit": {"type": "string"},
                "site": {"type": "string"},
            },
            "required": ["material"],
            "additionalProperties": True,
        },
    )


@pytest.fixture
def material_delivery_prompt(
    industry: Industry,
    material_delivery_category: Category,
) -> PromptTemplate:
    return PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="Construction material delivery",
        version=1,
        system_prompt=(
            "Extract a construction material delivery. "
            "Schema: {schema}. Dictionary: {dictionary}."
        ),
        user_prompt="Transcript: {transcript}",
    )


@pytest.fixture
def labor_payment_prompt(
    industry: Industry,
    labor_payment_category: Category,
) -> PromptTemplate:
    return PromptTemplate.objects.create(
        industry=industry,
        category=labor_payment_category,
        purpose=PromptPurpose.EXTRACTION,
        title="Construction labor payment",
        version=1,
        system_prompt="Extract a labor payment note.",
        user_prompt="Transcript: {transcript}",
    )


@pytest.fixture
def global_extraction_prompt(db) -> PromptTemplate:
    return PromptTemplate.objects.create(
        industry=None,
        category=None,
        purpose=PromptPurpose.EXTRACTION,
        title="Global fallback",
        version=1,
        system_prompt="Generic extraction.",
        user_prompt="Transcript: {transcript}",
    )


@pytest.fixture
def industry_dictionary_entries(industry: Industry) -> list[DomainDictionary]:
    return [
        DomainDictionary.objects.create(
            industry=industry,
            category=None,
            term="OPC",
            normalized_term="Ordinary Portland Cement",
        ),
        DomainDictionary.objects.create(
            industry=industry,
            category=None,
            term="fundi",
            normalized_term="skilled worker",
        ),
        DomainDictionary.objects.create(
            industry=industry,
            category=None,
            term="m",
            normalized_term="meter",
        ),
        DomainDictionary.objects.create(
            industry=industry,
            category=None,
            term="m3",
            normalized_term="cubic meters",
        ),
    ]


@pytest.fixture
def material_delivery_rule(
    industry: Industry,
    material_delivery_category: Category,
) -> ProcessingRule:
    return ProcessingRule.objects.create(
        industry=industry,
        category=material_delivery_category,
        rule_type=RuleType.KEYWORD_MATCH,
        priority=10,
        rule_config={
            "keywords": ["cement", "sand", "delivered", "bags", "opc"],
            "weight": 0.5,
        },
    )


@pytest.fixture
def labor_payment_rule(
    industry: Industry,
    labor_payment_category: Category,
) -> ProcessingRule:
    return ProcessingRule.objects.create(
        industry=industry,
        category=labor_payment_category,
        rule_type=RuleType.KEYWORD_MATCH,
        priority=10,
        rule_config={
            "keywords": ["paid", "wages", "fundi", "cash"],
            "weight": 0.5,
        },
    )
