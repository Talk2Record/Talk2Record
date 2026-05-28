"""Apply :class:`DomainDictionary` entries to a transcript.

The normalizer:

* Picks entries narrowest-scope-first so a category-scoped rule wins over an
  industry-scoped one which wins over a global one.
* Applies longer terms before shorter terms, so ``m3`` is matched before
  ``m`` and the latter never destroys the former.
* Matches case-insensitively against word boundaries.
* Returns the rewritten text *plus* an audit list of every replacement
  performed so it can be persisted on the ``normalization`` artifact for
  replay.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field

from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import DomainDictionary
from talk2record.taxonomy.models import Industry


@dataclass(frozen=True)
class _Entry:
    term: str
    normalized_term: str
    scope: str  # "category" | "industry" | "global"


@dataclass
class NormalizedText:
    text: str
    applied: list[dict] = field(default_factory=list)


class DictionaryNormalizer:
    @classmethod
    def normalize(
        cls,
        text: str,
        *,
        industry: Industry | None = None,
        category: Category | None = None,
    ) -> NormalizedText:
        if not text:
            return NormalizedText(text=text)

        entries = cls._load_entries(industry=industry, category=category)
        if not entries:
            return NormalizedText(text=text)

        result_text = text
        applied: list[dict] = []

        for entry in entries:
            pattern = re.compile(
                rf"(?<!\w){re.escape(entry.term)}(?!\w)",
                flags=re.IGNORECASE,
            )
            new_text, count = pattern.subn(entry.normalized_term, result_text)
            if count > 0:
                result_text = new_text
                applied.append(
                    {
                        "term": entry.term,
                        "normalized_term": entry.normalized_term,
                        "scope": entry.scope,
                        "count": count,
                    },
                )

        return NormalizedText(text=result_text, applied=applied)

    @classmethod
    def _load_entries(
        cls,
        *,
        industry: Industry | None,
        category: Category | None,
    ) -> list[_Entry]:
        """Load enabled entries in *narrowest-scope-first, longest-term-first* order."""

        effective_industry = industry or (category.industry if category else None)

        qs_filters = []
        if category is not None:
            qs_filters.append(
                ("category", {"industry": category.industry, "category": category}),
            )
        if effective_industry is not None:
            qs_filters.append(
                (
                    "industry",
                    {"industry": effective_industry, "category__isnull": True},
                ),
            )
        qs_filters.append(
            ("global", {"industry__isnull": True, "category__isnull": True}),
        )

        seen: set[str] = set()
        entries: list[_Entry] = []
        for scope, filt in qs_filters:
            rows = DomainDictionary.objects.filter(enabled=True, **filt).only(
                "term",
                "normalized_term",
            )
            for row in rows:
                key = row.term.lower()
                if key in seen:
                    continue
                seen.add(key)
                entries.append(
                    _Entry(
                        term=row.term,
                        normalized_term=row.normalized_term,
                        scope=scope,
                    ),
                )

        entries.sort(key=lambda e: (-len(e.term), e.term.lower()))
        return entries
