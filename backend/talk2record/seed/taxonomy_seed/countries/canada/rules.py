"""Deterministic classifier rules tuned for Canadian construction voice notes.

Keyword lists pick up CSA metric rebar codes, CSA cement types, Canadian
building-code acronyms, payroll/tax slips and Québécois French trade
vocabulary. The regex rule catches the M-prefix CSA G30.18 rebar
designations (10M, 15M, 20M, …).
"""

from __future__ import annotations

_INDUSTRY = "construction"

PROCESSING_RULE_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "keyword_match",
        "priority": 90,  # after Kenya (10-30), UK (40-50), USA (60-80)
        "rule_config": {
            "keywords": [
                # CSA metric rebar
                "10m", "15m", "20m", "25m", "30m", "35m", "45m", "55m",
                "type r", "type w", "400r", "400w", "500w", "600w",
                # CSA cement types
                "type gu", "type mh", "type he", "type lh", "type hs",
                # CSA standards & codes
                "csa", "csa a23.1", "csa o141", "nbc", "nbcc", "obc",
                "bcbc", "qcc", "cec",
                # Canadian lumber
                "spf", "s-p-f", "df-l", "hem-fir",
                # French materials
                "ciment", "béton", "brique", "acier", "sable", "gravier",
                "granulat", "armature",
            ],
            "weight": 0.45,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "labor_payment",
        "rule_type": "keyword_match",
        "priority": 90,
        "rule_config": {
            "keywords": [
                # Trades (English Canada)
                "red seal", "journeyperson", "millwright", "ironworker",
                "glazier", "labourer",
                # Quebec French trades
                "maçon", "charpentier", "électricien", "plombier",
                "plâtrier", "peintre", "ferrailleur", "couvreur",
                "briqueteur", "manœuvre", "contremaître",
                # Payment rails & tax slips
                "interac", "e-transfer", "eft", "certified cheque",
                "hst", "gst", "pst", "qst", "t4", "t4a", "t5018",
                "cra",
                # Workers' comp
                "wsib", "wcb", "cnesst", "worksafebc",
            ],
            "weight": 0.5,
        },
    },
    {
        "industry": _INDUSTRY,
        "category": "site_progress",
        "rule_type": "keyword_match",
        "priority": 90,
        "rule_config": {
            "keywords": [
                # French structural & actions
                "chantier", "coffrage", "ferraillage", "carrelage",
                "couler béton", "creuser", "poutre", "colonne", "dalle",
                "fondation", "semelle", "toiture", "plancher", "plafond",
                "escalier", "cloison",
                # Contracts / docs
                "ccdc", "ccdc 2", "ccdc 3", "raic", "csc",
            ],
            "weight": 0.4,
        },
    },
    {
        # Catches CSA G30.18 metric rebar callouts like "10M", "25M".
        "industry": _INDUSTRY,
        "category": "material_delivery",
        "rule_type": "regex_match",
        "priority": 100,
        "rule_config": {
            "pattern": r"\b(10|15|20|25|30|35|45|55)M\b",
            "weight": 0.3,
        },
    },
)
