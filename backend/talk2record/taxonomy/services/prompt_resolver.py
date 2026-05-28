"""Resolve the right :class:`~talk2record.taxonomy.models.PromptTemplate`.

Resolution order, most-specific first, with the highest enabled ``version``
winning at each tier:

1. ``(industry, category, purpose)``
2. ``(industry, null, purpose)``
3. ``(null, null, purpose)``

Returns ``None`` if no prompt is found — callers decide whether that is a
hard failure or a fallback condition.

Prompts support ``{transcript}``, ``{schema}``, ``{dictionary}``,
``{industry}``, ``{category}``, ``{catalog}`` placeholders. Rendering is
done with :meth:`str.format_map` against a permissive mapping so prompts
that omit a placeholder still render cleanly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import Industry
from talk2record.taxonomy.models import PromptPurpose
from talk2record.taxonomy.models import PromptTemplate


@dataclass(frozen=True)
class ResolvedPrompt:
    template: PromptTemplate
    system_prompt: str
    user_prompt: str
    version_label: str

    @property
    def industry_slug(self) -> str | None:
        return self.template.industry.slug if self.template.industry_id else None

    @property
    def category_slug(self) -> str | None:
        return self.template.category.slug if self.template.category_id else None


class _PermissiveDict(dict):
    """Dict subclass that returns ``""`` for missing keys during format_map."""

    def __missing__(self, key: str) -> str:
        return ""


class PromptResolver:
    @classmethod
    def resolve(
        cls,
        *,
        purpose: str,
        industry: Industry | None = None,
        category: Category | None = None,
        variables: Mapping[str, object] | None = None,
    ) -> ResolvedPrompt | None:
        """Find the most specific enabled template for ``purpose``.

        ``variables`` is the placeholder map used to render the prompt
        bodies. Both ``system_prompt`` and ``user_prompt`` are rendered.
        """

        template = cls._lookup(purpose=purpose, industry=industry, category=category)
        if template is None:
            return None

        ctx = _PermissiveDict(variables or {})
        ctx.setdefault(
            "industry",
            template.industry.slug if template.industry_id else "",
        )
        ctx.setdefault(
            "category",
            template.category.slug if template.category_id else "",
        )

        return ResolvedPrompt(
            template=template,
            system_prompt=_safe_format(template.system_prompt, ctx),
            user_prompt=_safe_format(template.user_prompt, ctx),
            version_label=f"v{template.version}",
        )

    @classmethod
    def _lookup(
        cls,
        *,
        purpose: str,
        industry: Industry | None,
        category: Category | None,
    ) -> PromptTemplate | None:
        if purpose not in {choice.value for choice in PromptPurpose}:
            return None

        qs = PromptTemplate.objects.filter(purpose=purpose, enabled=True)

        if category is not None:
            specific = (
                qs.filter(industry=category.industry, category=category)
                .order_by("-version")
                .first()
            )
            if specific is not None:
                return specific

        effective_industry = industry or (category.industry if category else None)
        if effective_industry is not None:
            scoped = (
                qs.filter(industry=effective_industry, category__isnull=True)
                .order_by("-version")
                .first()
            )
            if scoped is not None:
                return scoped

        return (
            qs.filter(industry__isnull=True, category__isnull=True)
            .order_by("-version")
            .first()
        )


def _safe_format(template: str, ctx: Mapping[str, object]) -> str:
    if not template:
        return ""
    try:
        return template.format_map(ctx)
    except (IndexError, KeyError, ValueError):
        return template
