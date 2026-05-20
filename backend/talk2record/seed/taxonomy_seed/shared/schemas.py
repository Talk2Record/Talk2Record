"""Construction extraction schemas shared across countries.

Field structure is universal; units and currencies are intentionally
free-form strings so a Kenyan ``"bags"`` payload, a UK ``"m3"`` payload and
a US ``"cu yd"`` payload all validate against the same schema.
"""

from __future__ import annotations

_OBJECT_NUMBER = {"type": "number"}
_OBJECT_STRING = {"type": "string"}

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
                "material": {"type": "string", "description": "Material delivered (e.g. cement, sand, rebar, lumber)."},
                "quantity": _OBJECT_NUMBER,
                "unit": {"type": "string", "description": "Unit of measure (bags, m3, cu yd, tons, pieces, …)."},
                "site": _OBJECT_STRING,
                "supplier": _OBJECT_STRING,
                "vehicle": _OBJECT_STRING,
                "delivered_at": _OBJECT_STRING,
                "notes": _OBJECT_STRING,
            },
            "required": ["material"],
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
                "worker": {"type": "string", "description": "Name or role of the worker paid."},
                "worker_role": {"type": "string", "description": "Trade / role: mason, carpenter, sparky, fundi, …"},
                "amount": _OBJECT_NUMBER,
                "currency": {"type": "string", "description": "ISO 4217 code (KES, USD, GBP, …) inferred from context."},
                "payment_method": _OBJECT_STRING,
                "site": _OBJECT_STRING,
                "task": {"type": "string", "description": "What the worker was paid for."},
                "paid_at": _OBJECT_STRING,
                "notes": _OBJECT_STRING,
            },
            "required": ["amount"],
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
                "site": _OBJECT_STRING,
                "activity": {"type": "string", "description": "Concrete activity completed."},
                "location": {"type": "string", "description": "e.g. slab B2, ground floor."},
                "materials_used": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": True,
                        "properties": {
                            "material": _OBJECT_STRING,
                            "quantity": _OBJECT_NUMBER,
                            "unit": _OBJECT_STRING,
                        },
                    },
                },
                "completed_at": _OBJECT_STRING,
                "notes": _OBJECT_STRING,
            },
            "required": ["activity"],
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
                "equipment": {"type": "string", "description": "Type or name of equipment."},
                "site": _OBJECT_STRING,
                "operator": _OBJECT_STRING,
                "duration_hours": _OBJECT_NUMBER,
                "cost": _OBJECT_NUMBER,
                "currency": {"type": "string", "description": "ISO 4217 code (KES, USD, GBP, …)."},
                "supplier": _OBJECT_STRING,
                "used_at": _OBJECT_STRING,
                "notes": _OBJECT_STRING,
            },
            "required": ["equipment"],
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
                "site": _OBJECT_STRING,
                "purpose": {"type": "string", "description": "Foundation, trench, footing, …"},
                "length_m": _OBJECT_NUMBER,
                "width_m": _OBJECT_NUMBER,
                "depth_m": _OBJECT_NUMBER,
                "volume_m3": _OBJECT_NUMBER,
                "operator": _OBJECT_STRING,
                "equipment": _OBJECT_STRING,
                "notes": _OBJECT_STRING,
            },
        },
    },
)
