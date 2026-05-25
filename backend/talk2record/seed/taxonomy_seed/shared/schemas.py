"""Construction extraction schemas shared across countries.

Field structure is universal; units and currencies are intentionally
free-form strings so a UK ``"m3"`` payload and a US ``"cu yd"`` payload
both validate against the same schema.

Extraction prompts instruct the LLM to emit ``null`` for unknown fields, so
every property accepts ``null`` at the JSON Schema layer. ``required_fields``
is kept as admin metadata for review UX — it is not enforced via
``json_schema.required``.
"""

from __future__ import annotations

_NULLABLE_STRING = {"type": ["string", "null"]}
_NULLABLE_NUMBER = {"type": ["number", "null"]}

SCHEMA_DEFINITIONS: tuple[dict, ...] = (
    {
        "category": ("construction", "material_delivery"),
        "name": "Material delivery v1",
        "version": 1,
        "is_default": True,
        "required_fields": ["material"],
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "material": {
                    "type": ["string", "null"],
                    "description": "Material delivered (e.g. cement, sand, rebar, lumber).",
                },
                "quantity": _NULLABLE_NUMBER,
                "unit": {
                    "type": ["string", "null"],
                    "description": "Unit of measure (bags, m3, cu yd, tons, pieces, …).",
                },
                "site": _NULLABLE_STRING,
                "supplier": _NULLABLE_STRING,
                "vehicle": _NULLABLE_STRING,
                "delivered_at": _NULLABLE_STRING,
                "notes": _NULLABLE_STRING,
            },
        },
    },
    {
        "category": ("construction", "labor_payment"),
        "name": "Labor payment v1",
        "version": 1,
        "is_default": True,
        "required_fields": ["amount"],
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "worker": {
                    "type": ["string", "null"],
                    "description": "Name or role of the worker paid.",
                },
                "worker_role": {
                    "type": ["string", "null"],
                    "description": "Trade / role: mason, carpenter, sparky, fundi, …",
                },
                "amount": _NULLABLE_NUMBER,
                "currency": {
                    "type": ["string", "null"],
                    "description": "ISO 4217 code (KES, USD, GBP, …) inferred from context.",
                },
                "payment_method": _NULLABLE_STRING,
                "site": _NULLABLE_STRING,
                "task": {
                    "type": ["string", "null"],
                    "description": "What the worker was paid for.",
                },
                "paid_at": _NULLABLE_STRING,
                "notes": _NULLABLE_STRING,
            },
        },
    },
    {
        "category": ("construction", "site_progress"),
        "name": "Site progress v1",
        "version": 1,
        "is_default": True,
        "required_fields": ["activity"],
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "site": _NULLABLE_STRING,
                "activity": {
                    "type": ["string", "null"],
                    "description": "Concrete activity completed.",
                },
                "location": {
                    "type": ["string", "null"],
                    "description": "e.g. slab B2, ground floor.",
                },
                "materials_used": {
                    "type": ["array", "null"],
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "material": _NULLABLE_STRING,
                            "quantity": _NULLABLE_NUMBER,
                            "unit": _NULLABLE_STRING,
                        },
                    },
                },
                "completed_at": _NULLABLE_STRING,
                "notes": _NULLABLE_STRING,
            },
        },
    },
    {
        "category": ("construction", "equipment_use"),
        "name": "Equipment use v1",
        "version": 1,
        "is_default": True,
        "required_fields": ["equipment"],
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "equipment": {
                    "type": ["string", "null"],
                    "description": "Type or name of equipment.",
                },
                "site": _NULLABLE_STRING,
                "operator": _NULLABLE_STRING,
                "duration_hours": _NULLABLE_NUMBER,
                "cost": _NULLABLE_NUMBER,
                "currency": {
                    "type": ["string", "null"],
                    "description": "ISO 4217 code (KES, USD, GBP, …).",
                },
                "supplier": _NULLABLE_STRING,
                "used_at": _NULLABLE_STRING,
                "notes": _NULLABLE_STRING,
            },
        },
    },
    {
        "category": ("construction", "excavation"),
        "name": "Excavation v1",
        "version": 1,
        "is_default": True,
        "required_fields": [],
        "json_schema": {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "additionalProperties": True,
            "properties": {
                "site": _NULLABLE_STRING,
                "purpose": {
                    "type": ["string", "null"],
                    "description": "Foundation, trench, footing, …",
                },
                "length_m": _NULLABLE_NUMBER,
                "width_m": _NULLABLE_NUMBER,
                "depth_m": _NULLABLE_NUMBER,
                "volume_m3": _NULLABLE_NUMBER,
                "operator": _NULLABLE_STRING,
                "equipment": _NULLABLE_STRING,
                "notes": _NULLABLE_STRING,
            },
        },
    },
)
