"""Construction dictionary terms that apply across all countries.

These are abbreviations and acronyms that are common to every English-speaking
construction market we ship to today — primarily SI/imperial units,
BS-standard cement designations widely understood in Kenya and the UK,
BRC welded mesh codes, and the (legacy but still common) Y-prefix and
R-prefix BS 4449 rebar sizes.

Country-specific overlays live in ``countries/<cc>/dictionary.py`` and
should only repeat a term here if the local normalisation genuinely differs.
"""

from __future__ import annotations

_INDUSTRY = "construction"

DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    # --- SI / metric units of measure ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "m3",
        "normalized_term": "cubic meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "m2",
        "normalized_term": "square meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cu m",
        "normalized_term": "cubic meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cum",
        "normalized_term": "cubic meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sq m",
        "normalized_term": "square meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "sqm",
        "normalized_term": "square meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lin m",
        "normalized_term": "linear meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lm",
        "normalized_term": "linear meters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "mm",
        "normalized_term": "millimeters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "cm",
        "normalized_term": "centimeters",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "kg",
        "normalized_term": "kilograms",
    },
    {"industry": _INDUSTRY, "category": None, "term": "ton", "normalized_term": "tons"},
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "tonne",
        "normalized_term": "tons",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "tonnes",
        "normalized_term": "tons",
    },
    # --- BS cement designations (BS 8500 / Concrete Society) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "OPC",
        "normalized_term": "Ordinary Portland Cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "PPC",
        "normalized_term": "Portland Pozzolana Cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "GGBS",
        "normalized_term": "Ground Granulated Blastfurnace Slag cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "PFA",
        "normalized_term": "Pulverised Fuel Ash cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "SRC",
        "normalized_term": "Sulfate Resistant Cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "RHC",
        "normalized_term": "Rapid Hardening Cement",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CEM I",
        "normalized_term": "CEM I Portland cement (BS 8500)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CEM II",
        "normalized_term": "CEM II blended Portland cement (BS 8500)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "CEM III",
        "normalized_term": "CEM III blastfurnace cement (BS 8500)",
    },
    # --- BS legacy rebar (Y high-yield, R mild steel) ---
    # Still used widely on Kenyan sites and on UK drawings predating the
    # current BS 4449:2005 H/B500 notation.
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "rebar",
        "normalized_term": "reinforcement bar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y8",
        "normalized_term": "8mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y10",
        "normalized_term": "10mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y12",
        "normalized_term": "12mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y16",
        "normalized_term": "16mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y20",
        "normalized_term": "20mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "Y25",
        "normalized_term": "25mm high-yield deformed rebar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "R6",
        "normalized_term": "6mm mild steel round bar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "R8",
        "normalized_term": "8mm mild steel round bar",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "R10",
        "normalized_term": "10mm mild steel round bar",
    },
    # --- BRC welded mesh (BS 4483) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "BRC",
        "normalized_term": "reinforcement mesh",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "A142",
        "normalized_term": "BRC mesh A142 (light-duty, 6mm wires)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "A193",
        "normalized_term": "BRC mesh A193 (medium-duty, 7mm wires)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "A252",
        "normalized_term": "BRC mesh A252 (heavy-duty, 8mm wires)",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "A393",
        "normalized_term": "BRC mesh A393 (structural, 10mm wires)",
    },
    # --- Generic generic structural English (BS / Commonwealth + US) ---
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "lintel",
        "normalized_term": "lintel beam",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "parapet",
        "normalized_term": "parapet wall",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "soffit",
        "normalized_term": "soffit",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "fascia",
        "normalized_term": "fascia board",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "eaves",
        "normalized_term": "roof eaves",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "ring beam",
        "normalized_term": "ring beam",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "plinth beam",
        "normalized_term": "plinth beam",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "hardcore",
        "normalized_term": "hardcore filling",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "DPM",
        "normalized_term": "damp proof membrane",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "DPC",
        "normalized_term": "damp proof course",
    },
    {
        "industry": _INDUSTRY,
        "category": None,
        "term": "shuttering",
        "normalized_term": "formwork",
    },
)
