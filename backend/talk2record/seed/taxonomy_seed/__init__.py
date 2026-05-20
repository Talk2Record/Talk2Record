"""Static definitions of taxonomy reference data, organised per country.

This package is the source of truth for **shipped** industries, categories,
extraction schemas, prompts, dictionary entries and processing rules. Every
entry is also editable in Django admin; on re-seed, admin overrides survive
(see :mod:`talk2record.seed.reference_data` for the upsert policy).

Layout
------

* ``industries.py``   — the seven business domains (country-neutral).
* ``shared/``         — construction structure shared across countries
  (categories, JSON schemas, extraction prompts).
* ``prompts_global.py`` — global prompts (classification + fallback
  extraction) used regardless of industry.
* ``countries/<cc>/`` — per-country terminology overlays
  (``dictionary.py`` + ``rules.py``). Add a new folder to ship a new locale.

Public API
----------

For backwards compatibility, this package exposes the same six aggregate
tuples that :mod:`talk2record.seed.reference_data` consumes:

* ``INDUSTRY_DEFINITIONS``
* ``CATEGORY_DEFINITIONS``
* ``SCHEMA_DEFINITIONS``
* ``PROMPT_DEFINITIONS``
* ``DICTIONARY_DEFINITIONS``
* ``PROCESSING_RULE_DEFINITIONS``

The aggregator simply concatenates the per-country files. Editors who want
to tweak Kenya-only terminology can edit ``countries/kenya/dictionary.py``
in isolation, without scrolling past USA or UK data.
"""

from __future__ import annotations

from talk2record.seed.taxonomy_seed.countries.canada import (
    DICTIONARY_DEFINITIONS as _CANADA_DICTIONARY,
)
from talk2record.seed.taxonomy_seed.countries.canada import (
    PROCESSING_RULE_DEFINITIONS as _CANADA_RULES,
)
from talk2record.seed.taxonomy_seed.countries.kenya import (
    DICTIONARY_DEFINITIONS as _KENYA_DICTIONARY,
)
from talk2record.seed.taxonomy_seed.countries.kenya import (
    PROCESSING_RULE_DEFINITIONS as _KENYA_RULES,
)
from talk2record.seed.taxonomy_seed.countries.uk import (
    DICTIONARY_DEFINITIONS as _UK_DICTIONARY,
)
from talk2record.seed.taxonomy_seed.countries.uk import (
    PROCESSING_RULE_DEFINITIONS as _UK_RULES,
)
from talk2record.seed.taxonomy_seed.countries.usa import (
    DICTIONARY_DEFINITIONS as _USA_DICTIONARY,
)
from talk2record.seed.taxonomy_seed.countries.usa import (
    PROCESSING_RULE_DEFINITIONS as _USA_RULES,
)
from talk2record.seed.taxonomy_seed.industries import INDUSTRY_DEFINITIONS
from talk2record.seed.taxonomy_seed.prompts_global import GLOBAL_PROMPT_DEFINITIONS
from talk2record.seed.taxonomy_seed.shared.categories import CATEGORY_DEFINITIONS
from talk2record.seed.taxonomy_seed.shared.dictionary import (
    DICTIONARY_DEFINITIONS as _SHARED_DICTIONARY,
)
from talk2record.seed.taxonomy_seed.shared.prompts import (
    CONSTRUCTION_PROMPT_DEFINITIONS,
)
from talk2record.seed.taxonomy_seed.shared.schemas import SCHEMA_DEFINITIONS

# Shared first, then per-country overlays in alphabetical country order so
# the seed output is deterministic and the dedup at ``get_or_create`` time
# prefers the universal normalisation when a term collides.
DICTIONARY_DEFINITIONS: tuple[dict, ...] = (
    *_SHARED_DICTIONARY,
    *_CANADA_DICTIONARY,
    *_KENYA_DICTIONARY,
    *_UK_DICTIONARY,
    *_USA_DICTIONARY,
)

PROCESSING_RULE_DEFINITIONS: tuple[dict, ...] = (
    *_CANADA_RULES,
    *_KENYA_RULES,
    *_UK_RULES,
    *_USA_RULES,
)

PROMPT_DEFINITIONS: tuple[dict, ...] = (
    *GLOBAL_PROMPT_DEFINITIONS,
    *CONSTRUCTION_PROMPT_DEFINITIONS,
)


__all__ = [
    "CATEGORY_DEFINITIONS",
    "DICTIONARY_DEFINITIONS",
    "INDUSTRY_DEFINITIONS",
    "PROCESSING_RULE_DEFINITIONS",
    "PROMPT_DEFINITIONS",
    "SCHEMA_DEFINITIONS",
]
