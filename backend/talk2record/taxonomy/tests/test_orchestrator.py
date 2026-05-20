"""End-to-end tests for :class:`ExtractionPipeline`."""

from __future__ import annotations

import pytest

from talk2record.taxonomy.services.orchestrator import ExtractionPipeline


@pytest.mark.django_db
def test_full_pipeline_material_delivery(
    industry,
    material_delivery_category,
    material_delivery_schema,
    material_delivery_prompt,
    material_delivery_rule,
    industry_dictionary_entries,
):
    outcome = ExtractionPipeline.run("Delivered 20 bags OPC to site A")

    assert outcome.classification.source in {"rules", "rules+llm"}
    assert any(c.slug == "material_delivery" for c in outcome.classification.categories)
    assert "Ordinary Portland Cement" in outcome.normalized_transcript
    assert outcome.extractions
    # Mock provider cannot fill in `material` so validation must fail and
    # the record must be flagged for review.
    assert outcome.needs_review is True
    assert any(err["message"] for err in outcome.validation_errors)


@pytest.mark.django_db
def test_pipeline_marks_review_when_no_categories_match(db):
    outcome = ExtractionPipeline.run("Some completely unclassifiable text")
    assert outcome.classification.industries == []
    assert outcome.extractions == []
    assert outcome.needs_review is True


@pytest.mark.django_db
def test_pipeline_persists_normalization_applied(
    industry,
    material_delivery_category,
    material_delivery_schema,
    material_delivery_prompt,
    material_delivery_rule,
    industry_dictionary_entries,
):
    outcome = ExtractionPipeline.run("Delivered 20 bags OPC to site")
    assert any(entry["term"] == "OPC" for entry in outcome.normalization.applied)


@pytest.mark.django_db
def test_multi_category_pipeline_runs_both_extractions(
    industry,
    material_delivery_category,
    labor_payment_category,
    material_delivery_schema,
    material_delivery_prompt,
    labor_payment_prompt,
    material_delivery_rule,
    labor_payment_rule,
    industry_dictionary_entries,
):
    outcome = ExtractionPipeline.run(
        "Delivered 20 bags cement and paid fundi 2000 cash",
    )
    slugs = {e.category_slug for e in outcome.extractions}
    assert {"material_delivery", "labor_payment"}.issubset(slugs)


@pytest.mark.django_db
def test_pipeline_confidence_below_threshold_marks_review(
    industry,
    material_delivery_category,
    material_delivery_schema,
    material_delivery_prompt,
    industry_dictionary_entries,
    settings,
):
    settings.TAXONOMY_REVIEW_CONFIDENCE = 0.99
    outcome = ExtractionPipeline.run("Delivered something")
    assert outcome.needs_review is True
