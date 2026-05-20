"""Kenyan / East African construction dictionary.

Focuses on terms that are **idiomatic to Kenyan voice notes**: Swahili
nouns and verbs, mjengo (construction site) slang, KEBS-specific rebar
notation, and M-Pesa payment rails.

Universal BS-standard terms shared with the UK (OPC/PPC/CEM I, A142 mesh,
Y-prefix rebar, m3/m2, BOQ, …) live in
:mod:`talk2record.seed.taxonomy_seed.shared.dictionary` so they aren't
duplicated three times.

Source notes (audit trail):

* KEBS rebar D-prefix Kenyan notation:
  https://www.constructionkenya.com/12986/rebar-types-sizes-grades/
  https://constructionreviewonline.com/knowhow/installations-materials/ribbed-steel-bars-reinforcement-reliable-reinforcement/
* "Mjengo" site lingo (chimba mtaro, kabiru ya wembe, weka niro, fisher
  board, mukwa, kofia, vumbi ya kware, dawa ya mchwa, …):
  https://sokodirectory.com/2019/06/chronicles-of-an-architect-understanding-the-mjengo-lingo-spoken-in-kenyas-construction-sites
"""

from __future__ import annotations

_INDUSTRY = "construction"

DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    # --- KEBS rebar (D-prefix, Kenyan market default) ---
    {"industry": _INDUSTRY, "category": None, "term": "D8", "normalized_term": "8mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D10", "normalized_term": "10mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D12", "normalized_term": "12mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D16", "normalized_term": "16mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D20", "normalized_term": "20mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D25", "normalized_term": "25mm deformed rebar"},
    {"industry": _INDUSTRY, "category": None, "term": "D32", "normalized_term": "32mm deformed rebar"},

    # --- bag convention (Kenyan cement is 50kg by default) ---
    {"industry": _INDUSTRY, "category": None, "term": "bag", "normalized_term": "50kg bag", "description": "Kenyan cement bags ship at 50kg by default."},

    # --- Swahili materials ---
    {"industry": _INDUSTRY, "category": None, "term": "saruji", "normalized_term": "cement"},
    {"industry": _INDUSTRY, "category": None, "term": "mchanga", "normalized_term": "sand"},
    {"industry": _INDUSTRY, "category": None, "term": "mawe", "normalized_term": "stones"},
    {"industry": _INDUSTRY, "category": None, "term": "jiwe", "normalized_term": "stone"},
    {"industry": _INDUSTRY, "category": None, "term": "machine cut", "normalized_term": "machine-cut stone block"},
    {"industry": _INDUSTRY, "category": None, "term": "matofali", "normalized_term": "bricks"},
    {"industry": _INDUSTRY, "category": None, "term": "tanga", "normalized_term": "brick"},
    {"industry": _INDUSTRY, "category": None, "term": "kokoto", "normalized_term": "aggregate"},
    {"industry": _INDUSTRY, "category": None, "term": "ballast", "normalized_term": "aggregate"},
    {"industry": _INDUSTRY, "category": None, "term": "bao", "normalized_term": "timber"},
    {"industry": _INDUSTRY, "category": None, "term": "msumari", "normalized_term": "nail"},
    {"industry": _INDUSTRY, "category": None, "term": "waya", "normalized_term": "binding wire"},
    {"industry": _INDUSTRY, "category": None, "term": "chuma", "normalized_term": "steel reinforcement"},
    {"industry": _INDUSTRY, "category": None, "term": "nondo", "normalized_term": "reinforcement bar"},
    {"industry": _INDUSTRY, "category": None, "term": "mukwa", "normalized_term": "hoop iron reinforcement", "description": "Hoop iron laid on alternate courses of thin masonry walls."},

    # --- Swahili structural / building parts ---
    {"industry": _INDUSTRY, "category": None, "term": "msingi", "normalized_term": "foundation"},
    {"industry": _INDUSTRY, "category": None, "term": "ukuta", "normalized_term": "wall"},
    {"industry": _INDUSTRY, "category": None, "term": "paa", "normalized_term": "roof"},
    {"industry": _INDUSTRY, "category": None, "term": "dari", "normalized_term": "ceiling"},
    {"industry": _INDUSTRY, "category": None, "term": "sakafu", "normalized_term": "floor"},
    {"industry": _INDUSTRY, "category": None, "term": "nguzo", "normalized_term": "column"},
    {"industry": _INDUSTRY, "category": None, "term": "mlango", "normalized_term": "door"},
    {"industry": _INDUSTRY, "category": None, "term": "dirisha", "normalized_term": "window"},
    {"industry": _INDUSTRY, "category": None, "term": "ngazi", "normalized_term": "stairs"},
    {"industry": _INDUSTRY, "category": None, "term": "kofia", "normalized_term": "parapet coping", "description": "Coping that terminates the top of a parapet or free-standing wall."},
    {"industry": _INDUSTRY, "category": None, "term": "fisher board", "normalized_term": "fascia board"},
    {"industry": _INDUSTRY, "category": None, "term": "karatasi ya polythene", "normalized_term": "damp proof membrane"},

    # --- mjengo verbs / processes ---
    {"industry": _INDUSTRY, "category": None, "term": "chimba mtaro", "normalized_term": "dig foundation trench"},
    {"industry": _INDUSTRY, "category": None, "term": "kuchimba", "normalized_term": "excavate"},
    {"industry": _INDUSTRY, "category": None, "term": "mtaro", "normalized_term": "foundation trench"},
    {"industry": _INDUSTRY, "category": None, "term": "koroga", "normalized_term": "concrete mixing and pouring"},
    {"industry": _INDUSTRY, "category": None, "term": "weka shutter", "normalized_term": "install formwork"},
    {"industry": _INDUSTRY, "category": None, "term": "weka niro", "normalized_term": "apply neat cement finish"},
    {"industry": _INDUSTRY, "category": None, "term": "funga joints", "normalized_term": "apply mortar joints"},
    {"industry": _INDUSTRY, "category": None, "term": "weka key", "normalized_term": "place rebar to key masonry joints"},
    {"industry": _INDUSTRY, "category": None, "term": "kabiru ya wembe", "normalized_term": "perfectly plumb wall", "description": "Site slang for a wall so vertical that only a razor blade fits between it and a plumb bob."},
    {"industry": _INDUSTRY, "category": None, "term": "vumbi ya kware", "normalized_term": "quarry dust blinding"},
    {"industry": _INDUSTRY, "category": None, "term": "dawa ya mchwa", "normalized_term": "termite control treatment"},

    # --- Swahili trades / roles ---
    {"industry": _INDUSTRY, "category": None, "term": "fundi", "normalized_term": "skilled worker"},
    {"industry": _INDUSTRY, "category": None, "term": "mkono", "normalized_term": "casual laborer"},
    {"industry": _INDUSTRY, "category": None, "term": "mtu wa kazi", "normalized_term": "worker"},
    {"industry": _INDUSTRY, "category": None, "term": "jua kali", "normalized_term": "informal artisan work", "description": "Literally 'hot sun'; refers to informal-sector workmanship."},
    {"industry": _INDUSTRY, "category": None, "term": "mfumaji", "normalized_term": "steel-fixer"},

    # --- Kenyan equipment slang ---
    {"industry": _INDUSTRY, "category": None, "term": "boflo", "normalized_term": "wheelbarrow"},
    {"industry": _INDUSTRY, "category": None, "term": "tipper", "normalized_term": "dump truck"},
    {"industry": _INDUSTRY, "category": None, "term": "JCB", "normalized_term": "backhoe loader", "description": "JCB is widely used as a generic name for backhoe loaders in Kenya."},
    {"industry": _INDUSTRY, "category": None, "term": "jembe", "normalized_term": "hoe"},
    {"industry": _INDUSTRY, "category": None, "term": "nyundo", "normalized_term": "hammer"},

    # --- M-Pesa / Kenyan payment rails (scoped to labor payments) ---
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "mpesa", "normalized_term": "M-Pesa mobile money"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "paybill", "normalized_term": "M-Pesa paybill payment"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "till", "normalized_term": "M-Pesa till payment"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "airtel money", "normalized_term": "Airtel Money"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "RTGS", "normalized_term": "RTGS bank transfer"},
    {"industry": _INDUSTRY, "category": "labor_payment", "term": "per diem", "normalized_term": "daily allowance"},
)
