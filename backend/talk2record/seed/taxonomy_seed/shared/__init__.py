"""Construction-industry structure shared across all countries.

Categories, JSON schemas and extraction prompts are intentionally
country-neutral. Localisation happens via the domain dictionary
(``countries/<cc>/dictionary.py``), which the prompt interpolates so the
LLM speaks the local vocabulary back to us.
"""
