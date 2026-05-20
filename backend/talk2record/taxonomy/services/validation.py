"""Validate an extracted payload against an :class:`ExtractionSchema`.

Wraps the ``jsonschema`` library so the result is a small, JSON-safe
dataclass that we can persist on the record (``validation_errors``) and
return to the frontend as-is.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any

import jsonschema
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from talk2record.taxonomy.models import ExtractionSchema


@dataclass
class ValidationResult:
    ok: bool
    errors: list[dict] = field(default_factory=list)


class SchemaValidator:
    @classmethod
    def validate(
        cls,
        payload: Any,
        *,
        schema: ExtractionSchema,
    ) -> ValidationResult:
        """Validate ``payload`` against ``schema.json_schema``.

        Always returns — never raises. Errors are collected as
        ``[{"path": "field.subfield", "message": "..."}, ...]``.
        """

        schema_dict = schema.json_schema or {}
        if not schema_dict:
            return ValidationResult(ok=True)

        try:
            validator = jsonschema.Draft7Validator(schema_dict)
        except jsonschema.SchemaError as exc:
            return ValidationResult(
                ok=False,
                errors=[{"path": "", "message": f"Invalid schema: {exc.message}"}],
            )

        errors: list[dict] = []
        for err in sorted(validator.iter_errors(payload), key=lambda e: e.path):
            errors.append(
                {
                    "path": _format_path(err),
                    "message": err.message,
                    "validator": err.validator,
                },
            )

        return ValidationResult(ok=not errors, errors=errors)

    @classmethod
    def validate_dict(
        cls,
        payload: Any,
        *,
        json_schema: dict,
    ) -> ValidationResult:
        """Same as :meth:`validate` but takes a raw JSON-Schema dict (for tests)."""

        schema_dict = json_schema or {}
        if not schema_dict:
            return ValidationResult(ok=True)
        try:
            validator = jsonschema.Draft7Validator(schema_dict)
        except jsonschema.SchemaError as exc:
            return ValidationResult(
                ok=False,
                errors=[{"path": "", "message": f"Invalid schema: {exc.message}"}],
            )
        errors = []
        for err in sorted(validator.iter_errors(payload), key=lambda e: e.path):
            errors.append(
                {
                    "path": _format_path(err),
                    "message": err.message,
                    "validator": err.validator,
                },
            )
        return ValidationResult(ok=not errors, errors=errors)


def _format_path(err: JSONSchemaValidationError) -> str:
    return ".".join(str(part) for part in err.path)
