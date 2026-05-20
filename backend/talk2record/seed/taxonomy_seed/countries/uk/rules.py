"""Deterministic classifier rules tuned for UK construction voice notes.

Keyword lists prioritise British trade slang and BS-current notation;
the regex rule catches H-prefix BS 4449 rebar codes.
"""

from __future__ import annotations

_INDUSTRY = "construction"

PROCESSING_RULE_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "keyword_match",
        "priority": 40,  # priority>30 so country rules slot in after Kenya's
        "rule_config": {
            "keywords": [
                # BS 4449 H/T current notation
                "h8", "h10", "h12", "h16", "h20", "h25", "h32", "h40",
                "t10", "t12", "t16", "t20", "t25",
                "b500a", "b500b", "b500c",
                # UK materials
                "mot type 1", "type 1", "pir", "celotex", "kingspan",
                "plasterboard", "osb3", "mr mdf", "sbr",
                # bonds
                "stretcher bond", "flemish bond", "english bond",
                "header bond", "soldier course",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "rule_type": "keyword_match",
        "priority": 40,
        "rule_config": {
            "keywords": [
                # UK trade slang
                "chippy", "sparky", "sparks", "brickie", "navvy",
                "navvies", "groundworker", "banksman", "ganger",
                "gaffer", "plumbie", "tradie", "site agent",
                # UK payment rails
                "bacs", "chaps", "faster payment", "cis",
                # contract / commercial
                "boq", "bq", "prelims", "p&g", "vo", "ipc",
                "dayworks", "retention",
            ],
            "weight": 0.5,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "site_progress",
        "rule_type": "keyword_match",
        "priority": 40,
        "rule_config": {
            "keywords": [
                "first fix", "second fix", "snagging", "snag list",
                "wet trades", "dry lining", "screed", "skim", "render",
                "part l", "part e", "part m", "nhbc", "cdm",
            ],
            "weight": 0.4,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "equipment_use",
        "rule_type": "keyword_match",
        "priority": 40,
        "rule_config": {
            "keywords": [
                "digger", "telehandler", "whacker plate",
                "vibrating plate", "breaker", "transit",
                "kango", "stihl saw",
            ],
            "weight": 0.45,
        },
    },
    {
        # Catches BS 4449 current rebar codes (H8, H12, H40, etc.).
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 50,
        "rule_config": {
            "pattern": r"\bH\s?(8|10|12|16|20|25|32|40)\b",
            "weight": 0.25,
        },
    },
)
