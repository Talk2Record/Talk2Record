"""Deterministic classifier rules tuned for Kenyan / East African voice notes.

Keyword lists prioritise Swahili and mjengo slang; the regex rules catch
KEBS D-prefix rebar codes and BS-legacy Y-prefix rebar codes commonly
mentioned on Kenyan sites.
"""

from __future__ import annotations

_INDUSTRY = "construction"

PROCESSING_RULE_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "keyword_match",
        "priority": 10,
        "rule_config": {
            "keywords": [
                # core English
                "cement", "sand", "aggregate", "ballast", "bricks",
                "blocks", "stones", "timber", "rebar", "mesh", "wire",
                "nails", "bags", "delivered", "delivery", "lorry",
                "tipper", "supplier",
                # cement abbreviations (BS, common in Kenya)
                "opc", "ppc", "ggbs", "pfa", "src", "rhc",
                # rebar / mesh designators (Kenya: D-prefix + BS legacy)
                "d8", "d10", "d12", "d16", "d20", "d25", "d32",
                "y8", "y10", "y12", "y16", "y20", "y25",
                "r6", "r8", "r10", "brc", "a142", "a193", "a252", "a393",
                # Swahili materials
                "saruji", "mchanga", "mawe", "jiwe", "matofali", "tanga",
                "kokoto", "bao", "nondo", "msumari", "waya", "chuma",
                "mukwa",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "rule_type": "keyword_match",
        "priority": 10,
        "rule_config": {
            "keywords": [
                "paid", "pay", "wages", "wage", "salary", "casual",
                "daily wage", "per diem", "allowance",
                # Swahili trades
                "fundi", "mkono", "mtu wa kazi", "mfumaji",
                # English trades
                "mason", "carpenter", "steelfixer", "steel fixer",
                "bar bender", "plasterer", "tiler", "painter",
                "scaffolder", "foreman",
                # Kenya-specific payment methods
                "cash", "mpesa", "paybill", "till", "airtel money",
                "rtgs",
            ],
            "weight": 0.5,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "site_progress",
        "rule_type": "keyword_match",
        "priority": 10,
        "rule_config": {
            "keywords": [
                # English
                "slab", "cast", "poured", "floor", "wall", "raised",
                "progress", "completed", "finished", "level", "screed",
                "plaster", "ring beam", "plinth", "lintel", "parapet",
                "soffit", "fascia", "eaves",
                # mjengo verbs
                "koroga", "weka shutter", "weka niro", "funga joints",
                "weka key", "kabiru ya wembe",
                # Swahili structural
                "ukuta", "paa", "dari", "sakafu", "nguzo", "msingi",
                "ngazi", "mlango", "dirisha",
            ],
            "weight": 0.4,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "equipment_use",
        "rule_type": "keyword_match",
        "priority": 10,
        "rule_config": {
            "keywords": [
                "grader", "mixer", "crane", "wheelbarrow", "boflo",
                "hired", "machine", "equipment", "excavator", "loader",
                "compactor", "vibrator", "tipper", "jcb", "backhoe",
                "scaffolding", "formwork", "shuttering",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "excavation",
        "rule_type": "keyword_match",
        "priority": 10,
        "rule_config": {
            "keywords": [
                "excavat", "dig", "trench", "foundation", "footing",
                "septic", "borehole", "kuchimba", "chimba mtaro", "mtaro",
                "raft", "hardcore", "blinding", "dpm", "dpc",
                "vumbi ya kware", "dawa ya mchwa",
            ],
            "weight": 0.5,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "excavation",
        "rule_type": "regex_match",
        "priority": 20,
        "rule_config": {
            # Catches "10 by 5 by 2 meters", "10x5x2 m" etc.
            "pattern": r"\b\d+(\.\d+)?\s*(by|x)\s*\d+(\.\d+)?\s*(by|x)\s*\d+",
            "weight": 0.3,
        },
    },
    {
        # Catches typical Kenyan rebar size mentions like "D12", "Y10",
        # "R8" in either case.
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 20,
        "rule_config": {
            "pattern": r"\b[YDR]\s?\d{1,2}\b",
            "weight": 0.25,
        },
    },
    {
        # Catches BRC mesh designations such as "A142", "A252", "A393".
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 30,
        "rule_config": {
            "pattern": r"\bA\s?(142|193|252|393)\b",
            "weight": 0.25,
        },
    },
)
