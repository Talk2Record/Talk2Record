from __future__ import annotations

import pytest

from talk2record.taxonomy.models import PromptPurpose
from talk2record.taxonomy.models import PromptTemplate
from talk2record.taxonomy.services.prompt_resolver import PromptResolver


@pytest.mark.django_db
def test_resolves_category_specific_prompt_over_industry(
    industry,
    material_delivery_category,
    material_delivery_prompt,
):
    # An industry-only prompt also exists but the category-specific one wins.
    PromptTemplate.objects.create(
        industry=industry,
        category=None,
        purpose=PromptPurpose.EXTRACTION,
        title="Industry-wide",
        version=5,
        system_prompt="industry-wide prompt",
    )

    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )

    assert resolved is not None
    assert (
        resolved.template_id == material_delivery_prompt.pk
        if hasattr(resolved, "template_id")
        else True
    )
    assert resolved.template.pk == material_delivery_prompt.pk


@pytest.mark.django_db
def test_falls_back_to_industry_prompt_when_no_category_prompt(
    industry,
    material_delivery_category,
):
    industry_prompt = PromptTemplate.objects.create(
        industry=industry,
        category=None,
        purpose=PromptPurpose.EXTRACTION,
        title="Industry-wide",
        version=1,
        system_prompt="industry-wide prompt",
    )

    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )

    assert resolved is not None
    assert resolved.template.pk == industry_prompt.pk


@pytest.mark.django_db
def test_falls_back_to_global_prompt_when_no_industry_prompt(
    global_extraction_prompt,
    material_delivery_category,
):
    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )

    assert resolved is not None
    assert resolved.template.pk == global_extraction_prompt.pk


@pytest.mark.django_db
def test_returns_none_when_no_prompt_exists(material_delivery_category):
    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )
    assert resolved is None


@pytest.mark.django_db
def test_disabled_prompts_are_skipped(industry, material_delivery_category):
    PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="Disabled prompt",
        version=2,
        system_prompt="disabled",
        enabled=False,
    )
    enabled = PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="Enabled prompt",
        version=1,
        system_prompt="enabled",
        enabled=True,
    )
    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )
    assert resolved is not None
    assert resolved.template.pk == enabled.pk


@pytest.mark.django_db
def test_highest_version_wins_within_tier(industry, material_delivery_category):
    PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="V1",
        version=1,
        system_prompt="v1",
    )
    v3 = PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="V3",
        version=3,
        system_prompt="v3",
    )
    PromptTemplate.objects.create(
        industry=industry,
        category=material_delivery_category,
        purpose=PromptPurpose.EXTRACTION,
        title="V2",
        version=2,
        system_prompt="v2",
    )

    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
    )

    assert resolved is not None
    assert resolved.template.pk == v3.pk
    assert resolved.version_label == "v3"


@pytest.mark.django_db
def test_renders_placeholders_in_prompts(
    material_delivery_category,
    material_delivery_prompt,
):
    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
        variables={
            "transcript": "delivered 20 bags",
            "schema": "{}",
            "dictionary": "(none)",
        },
    )
    assert resolved is not None
    assert "delivered 20 bags" in resolved.user_prompt
    assert "{}" in resolved.system_prompt
    assert "(none)" in resolved.system_prompt


@pytest.mark.django_db
def test_missing_placeholders_render_as_empty(
    material_delivery_category,
    material_delivery_prompt,
):
    resolved = PromptResolver.resolve(
        purpose=PromptPurpose.EXTRACTION,
        category=material_delivery_category,
        variables={"transcript": "x"},
    )
    assert resolved is not None
    # `{schema}` and `{dictionary}` are not provided — they must not crash.
    assert resolved.user_prompt.startswith("Transcript: x")
