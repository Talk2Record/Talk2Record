from __future__ import annotations

import pytest

from talk2record.taxonomy.services.validation import SchemaValidator


@pytest.mark.django_db
def test_valid_payload_returns_ok(material_delivery_schema):
    payload = {"material": "cement", "quantity": 20, "unit": "bags"}
    result = SchemaValidator.validate(payload, schema=material_delivery_schema)
    assert result.ok is True
    assert result.errors == []


@pytest.mark.django_db
def test_missing_required_field_returns_error(material_delivery_schema):
    payload = {"quantity": 20}
    result = SchemaValidator.validate(payload, schema=material_delivery_schema)
    assert result.ok is False
    assert any("material" in e["message"] for e in result.errors)


@pytest.mark.django_db
def test_wrong_type_returns_error(material_delivery_schema):
    payload = {"material": "cement", "quantity": "twenty"}
    result = SchemaValidator.validate(payload, schema=material_delivery_schema)
    assert result.ok is False
    assert any(e.get("path") == "quantity" for e in result.errors)


@pytest.mark.django_db
def test_empty_schema_treated_as_pass_through(material_delivery_schema):
    material_delivery_schema.json_schema = {}
    material_delivery_schema.save(update_fields=["json_schema"])
    result = SchemaValidator.validate(
        {"anything": "goes"},
        schema=material_delivery_schema,
    )
    assert result.ok is True


def test_validate_dict_passes_for_valid_payload():
    schema = {
        "type": "object",
        "properties": {"amount": {"type": "number"}},
        "required": ["amount"],
    }
    result = SchemaValidator.validate_dict({"amount": 2000}, json_schema=schema)
    assert result.ok is True


def test_validate_dict_reports_path_for_nested_errors():
    schema = {
        "type": "object",
        "properties": {
            "address": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
        "required": ["address"],
    }
    result = SchemaValidator.validate_dict(
        {"address": {}},
        json_schema=schema,
    )
    assert result.ok is False
    assert any("city" in (err.get("message") or "") for err in result.errors)
