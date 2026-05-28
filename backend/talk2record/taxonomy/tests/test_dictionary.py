from __future__ import annotations

import pytest

from talk2record.taxonomy.models import DomainDictionary
from talk2record.taxonomy.services.dictionary import DictionaryNormalizer


@pytest.mark.django_db
def test_normalizes_industry_scoped_terms(
    industry,
    industry_dictionary_entries,
):
    result = DictionaryNormalizer.normalize(
        "Delivered 20 bags OPC and paid fundi 2000",
        industry=industry,
    )
    assert "Ordinary Portland Cement" in result.text
    assert "skilled worker" in result.text
    assert {entry["term"] for entry in result.applied} == {"OPC", "fundi"}


@pytest.mark.django_db
def test_longer_terms_match_before_shorter(
    industry,
    industry_dictionary_entries,
):
    # ``m3`` must be matched before ``m`` — otherwise "10 m3" becomes
    # "10 meter3" instead of "10 cubic meters".
    result = DictionaryNormalizer.normalize(
        "Excavation 10 m3 of soil",
        industry=industry,
    )
    assert "cubic meters" in result.text
    assert "meter3" not in result.text


@pytest.mark.django_db
def test_category_scope_overrides_industry_scope(
    industry,
    material_delivery_category,
):
    DomainDictionary.objects.create(
        industry=industry,
        category=None,
        term="bags",
        normalized_term="sacks",
    )
    DomainDictionary.objects.create(
        industry=industry,
        category=material_delivery_category,
        term="bags",
        normalized_term="bag units",
    )
    result = DictionaryNormalizer.normalize(
        "20 bags",
        industry=industry,
        category=material_delivery_category,
    )
    assert "bag units" in result.text
    assert "sacks" not in result.text


@pytest.mark.django_db
def test_disabled_entries_are_ignored(industry):
    DomainDictionary.objects.create(
        industry=industry,
        category=None,
        term="OPC",
        normalized_term="cement",
        enabled=False,
    )
    result = DictionaryNormalizer.normalize("Delivered OPC", industry=industry)
    assert result.text == "Delivered OPC"
    assert result.applied == []


@pytest.mark.django_db
def test_case_insensitive_word_boundary_match(industry):
    DomainDictionary.objects.create(
        industry=industry,
        category=None,
        term="rebar",
        normalized_term="reinforcement bar",
    )
    result = DictionaryNormalizer.normalize(
        "Used Rebar and rebars",
        industry=industry,
    )
    # "Rebar" → matched (case-insensitive); "rebars" → NOT matched because
    # of the word boundary.
    assert "reinforcement bar" in result.text
    assert "rebars" in result.text


@pytest.mark.django_db
def test_empty_input_returns_empty(industry):
    result = DictionaryNormalizer.normalize("", industry=industry)
    assert result.text == ""
    assert result.applied == []
