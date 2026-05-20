"""Construction extraction prompts shared across countries.

These prompts deliberately avoid baking a single country's units or
currency into the system prompt. The ``{dictionary}`` placeholder is
populated at runtime with the union of all dictionary entries in scope
(industry + category + country, depending on which entries are enabled in
admin), so a US transcript gets US terms expanded and a UK transcript
gets UK terms expanded — without ever editing the prompt itself.
"""

from __future__ import annotations

from talk2record.seed.taxonomy_seed.prompts_global import GLOBAL_EXTRACTION_USER_PROMPT

_MATERIAL_DELIVERY_PROMPT = """\
You are extracting a CONSTRUCTION material-delivery note from a voice
transcript. Return JSON that matches the schema. Conventions:

- material: lowercase normalized form (e.g. "cement", "sand", "rebar",
  "lumber", "aggregate").
- quantity / unit: numeric and a short unit string. Use whatever unit the
  speaker used ("bags", "m3", "cu yd", "tons", "pieces", "linear feet")
  and do NOT silently convert.
- site: name or label of the site if mentioned.
- supplier: company or person who delivered.
- vehicle: lorry plate or description if mentioned.
- delivered_at: ISO date or time-of-day phrase if mentioned, else null.

Convert obvious abbreviations using the dictionary, but do NOT invent
units or quantities that were not stated.

Return ONLY valid JSON, no markdown.

Domain dictionary:
{dictionary}

JSON Schema:
{schema}
"""

_LABOR_PAYMENT_PROMPT = """\
You are extracting a CONSTRUCTION labor-payment note from a voice
transcript. Return JSON that matches the schema. Conventions:

- worker: name OR role if no name was given.
- worker_role: short role label normalized via the dictionary (e.g.
  "mason", "carpenter", "electrician", "fundi", "casual", "groundworker").
- amount: numeric, the amount paid.
- currency: ISO 4217 three-letter code as stated or strongly implied
  (KES, USD, GBP). Do NOT default a currency unless it is clearly stated.
- payment_method: short token ("cash", "mpesa", "cheque", "bank_transfer",
  "ach", "wire", "venmo", …) or null.
- task: short phrase ("slab casting", "rebar bending", "drywall hang", …).

Return ONLY valid JSON, no markdown.

Domain dictionary:
{dictionary}

JSON Schema:
{schema}
"""

_SITE_PROGRESS_PROMPT = """\
You are extracting a CONSTRUCTION site-progress update from a voice
transcript. Return JSON that matches the schema. Conventions:

- activity: short verb phrase ("cast slab", "raised wall", "screeded
  floor", "framed wall", "hung drywall").
- location: structural element or area within the site.
- materials_used: list each material with quantity and unit when stated.
- Do NOT invent quantities not in the transcript.

Return ONLY valid JSON, no markdown.

Domain dictionary:
{dictionary}

JSON Schema:
{schema}
"""

_EQUIPMENT_USE_PROMPT = """\
You are extracting a CONSTRUCTION equipment-use note from a voice
transcript. Return JSON that matches the schema. Conventions:

- equipment: normalized equipment name (e.g. "concrete mixer", "grader",
  "crane", "wheelbarrow", "skid-steer loader", "backhoe loader"). Translate
  slang and brand-as-noun ("JCB", "Bobcat", "Sawzall") via the dictionary.
- duration_hours: numeric hours if stated.
- cost: total cost of the equipment usage if stated.

Return ONLY valid JSON, no markdown.

Domain dictionary:
{dictionary}

JSON Schema:
{schema}
"""

_EXCAVATION_PROMPT = """\
You are extracting a CONSTRUCTION excavation note from a voice transcript.
Return JSON that matches the schema. Conventions:

- length_m / width_m / depth_m: numeric meters. Parse phrases like
  "10 by 5 by 2 meters" as length=10, width=5, depth=2. Convert from
  feet to metres only if explicitly stated; otherwise keep whatever unit
  the transcript provided and surface it via ``notes``.
- volume_m3: compute length*width*depth when all three are in metres;
  otherwise leave null.
- purpose: "foundation", "trench", "footing", "septic", "basement", …
  or leave null.

Return ONLY valid JSON, no markdown.

Domain dictionary:
{dictionary}

JSON Schema:
{schema}
"""


CONSTRUCTION_PROMPT_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": "construction",
        "category": "material_delivery",
        "purpose": "extraction",
        "title": "Construction material delivery extraction v1",
        "version": 1,
        "system_prompt": _MATERIAL_DELIVERY_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
        "example_input": "Delivered 20 bags OPC to site A.",
        "example_output": (
            '{"material":"cement","quantity":20,"unit":"bags","site":"site A",'
            '"supplier":null,"vehicle":null,"delivered_at":null,"notes":null}'
        ),
    },
    {
        "industry": "construction",
        "category": "labor_payment",
        "purpose": "extraction",
        "title": "Construction labor payment extraction v1",
        "version": 1,
        "system_prompt": _LABOR_PAYMENT_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
        "example_input": "Paid fundi 2,000 cash.",
        "example_output": (
            '{"worker":null,"worker_role":"fundi","amount":2000,"currency":"KES",'
            '"payment_method":"cash","site":null,"task":null,"paid_at":null,"notes":null}'
        ),
    },
    {
        "industry": "construction",
        "category": "site_progress",
        "purpose": "extraction",
        "title": "Construction site progress extraction v1",
        "version": 1,
        "system_prompt": _SITE_PROGRESS_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
        "example_input": "Cast slab B2 using 3 tons sand and 15 bags cement.",
        "example_output": (
            '{"site":null,"activity":"cast slab","location":"slab B2",'
            '"materials_used":[{"material":"sand","quantity":3,"unit":"tons"},'
            '{"material":"cement","quantity":15,"unit":"bags"}],"completed_at":null,"notes":null}'
        ),
    },
    {
        "industry": "construction",
        "category": "equipment_use",
        "purpose": "extraction",
        "title": "Construction equipment use extraction v1",
        "version": 1,
        "system_prompt": _EQUIPMENT_USE_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
    },
    {
        "industry": "construction",
        "category": "excavation",
        "purpose": "extraction",
        "title": "Construction excavation extraction v1",
        "version": 1,
        "system_prompt": _EXCAVATION_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
        "example_input": "Excavation 10 by 5 by 2 meters.",
        "example_output": (
            '{"site":null,"purpose":null,"length_m":10,"width_m":5,"depth_m":2,'
            '"volume_m3":100,"operator":null,"equipment":null,"notes":null}'
        ),
    },
)
