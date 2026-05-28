"""Deterministic classifier rules tuned for US construction voice notes.

Keyword lists prioritise US-specific vocabulary; the regex rules catch
ASTM C150 cement types (Type I-V) and ASTM A615 imperial rebar codes
(#3 through #11).
"""

from __future__ import annotations

_INDUSTRY = "construction"

PROCESSING_RULE_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "keyword_match",
        "priority": 60,  # after Kenya (10-30) and UK (40-50)
        "rule_config": {
            "keywords": [
                # cement / concrete
                "type i",
                "type ii",
                "type iii",
                "type iv",
                "type v",
                "psi",
                "ksi",
                "3000 psi",
                "4000 psi",
                "5000 psi",
                # rebar
                "grade 40",
                "grade 60",
                "grade 75",
                "grade 80",
                # imperial units
                "cu yd",
                "cy",
                "sq ft",
                "sf",
                "lin ft",
                "lf",
                # framing lumber
                "2x4",
                "2x6",
                "2x8",
                "2x10",
                "2x12",
                "4x4",
                "6x6",
                # sheet goods / drywall
                "osb",
                "cdx",
                "plywood",
                "drywall",
                "sheetrock",
                "gypsum",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "rule_type": "keyword_match",
        "priority": 60,
        "rule_config": {
            "keywords": [
                # roles
                "gc",
                "general contractor",
                "subcontractor",
                "subs",
                "journeyman",
                "apprentice",
                "super",
                "superintendent",
                "drywaller",
                "carpenter",
                "electrician",
                "plumber",
                # payment rails
                "ach",
                "wire",
                "wire transfer",
                "venmo",
                "zelle",
                "cash app",
                "1099",
                "w-2",
                # documents
                "schedule of values",
                "sov",
            ],
            "weight": 0.5,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "site_progress",
        "rule_type": "keyword_match",
        "priority": 60,
        "rule_config": {
            "keywords": [
                # framing verbs
                "framed",
                "framing",
                "hung",
                "rocked",
                "mudded",
                "taped",
                "textured",
                "sheathed",
                "decked",
                # vocabulary
                "stud",
                "joist",
                "rafter",
                "top plate",
                "bottom plate",
                "sole plate",
                "sheathing",
                "blocking",
                "header",
                "punch list",
                "punch",
                "rough-in",
                "rough in",
                # commercial / contract docs
                "rfi",
                "asi",
                "change order",
                "co",
                "cor",
                "g702",
                "g703",
                "aia a201",
            ],
            "weight": 0.4,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "equipment_use",
        "rule_type": "keyword_match",
        "priority": 60,
        "rule_config": {
            "keywords": [
                "sawzall",
                "skil saw",
                "skilsaw",
                "chop saw",
                "bobcat",
                "skid steer",
                "mini-ex",
                "lull",
                "scissor lift",
                "boom lift",
                "manlift",
                "jackhammer",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "excavation",
        "rule_type": "keyword_match",
        "priority": 60,
        "rule_config": {
            "keywords": [
                "basement",
                "footer",
                "slab on grade",
                "sog",
                "stem wall",
                "ahj",
                "permit",
                "code",
                "ibc",
                "irc",
            ],
            "weight": 0.4,
        },
    },
    {
        # Catches "#3", "#4", "#5" rebar mentions.
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 70,
        "rule_config": {
            "pattern": r"#\s?(3|4|5|6|7|8|9|10|11)\b",
            "weight": 0.25,
        },
    },
    {
        # Catches "3000 psi", "4000 psi" concrete strength callouts.
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 80,
        "rule_config": {
            "pattern": r"\b\d{3,5}\s?psi\b",
            "weight": 0.2,
        },
    },
)
