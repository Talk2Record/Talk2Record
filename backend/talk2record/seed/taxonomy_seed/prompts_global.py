"""Global prompts that apply regardless of industry or country.

Currently:

* ``classification`` — turn a transcript into (industry, category) pairs.
* ``extraction`` fallback — extract structured data when no industry- or
  category-specific extraction prompt is configured.

These prompts deliberately avoid hardcoding currencies, units or language
preferences. Per-country guidance lives in the corresponding dictionary
entries (``countries/<cc>/dictionary.py``), which are interpolated into
the prompt at runtime.
"""

from __future__ import annotations

CLASSIFICATION_SYSTEM_PROMPT = """\
You are a classifier for a multi-industry voice-note system.

Available industries and categories are provided as JSON below. For the
transcript that follows, choose the one or more (industry, category) pairs
that best match. Return ONLY valid JSON with no commentary, no markdown.

Output schema:
{
  "industries": [{"slug": "<industry_slug>", "confidence": 0.0-1.0}],
  "categories": [
    {"industry": "<industry_slug>", "slug": "<category_slug>", "confidence": 0.0-1.0}
  ]
}

Rules:
- Use only slugs from the catalog. Never invent new slugs.
- If unsure, return an empty industries/categories list (the system will mark
  the record for review).
- Multiple categories are allowed when the transcript covers more than one.

Catalog:
{catalog}
"""

CLASSIFICATION_USER_PROMPT = """\
Transcript:
{transcript}
"""

GLOBAL_EXTRACTION_FALLBACK_PROMPT = """\
You are a data extraction assistant. Extract structured data from the
transcript that conforms to the JSON Schema below.

Return ONLY valid JSON with no markdown, code fences, or commentary.
- Use null for fields you cannot determine.
- Do not invent values that are not stated or strongly implied.
- Where a domain dictionary maps abbreviations to full terms, prefer the
  full term in your output.

Industry: {industry}
Category: {category}

Domain dictionary (term -> normalized term):
{dictionary}

JSON Schema:
{schema}
"""

GLOBAL_EXTRACTION_USER_PROMPT = """\
Transcript:
{transcript}
"""


GLOBAL_PROMPT_DEFINITIONS: tuple[dict, ...] = (
    {
        "industry": None,
        "category": None,
        "purpose": "classification",
        "title": "Global classification v1",
        "version": 1,
        "system_prompt": CLASSIFICATION_SYSTEM_PROMPT,
        "user_prompt": CLASSIFICATION_USER_PROMPT,
        "example_input": "Delivered 20 bags OPC to site A.",
        "example_output": (
            '{"industries":[{"slug":"construction","confidence":0.95}],'
            '"categories":[{"industry":"construction","slug":"material_delivery","confidence":0.93}]}'
        ),
    },
    {
        "industry": None,
        "category": None,
        "purpose": "extraction",
        "title": "Global extraction fallback v1",
        "version": 1,
        "system_prompt": GLOBAL_EXTRACTION_FALLBACK_PROMPT,
        "user_prompt": GLOBAL_EXTRACTION_USER_PROMPT,
    },
)
