"""Idempotent seeding of platform/admin reference data.

This module is the **only** thing the ``seed_data`` command runs. It creates
or updates the records that staff would otherwise have to set up by hand on
every fresh install:

* Default legal document versions (terms, privacy, billing policy, …).
* Integration singletons (WhatsApp, Paddle, AI) — credentials are left blank
  so ops can fill them in via Django admin.
* Billing plans, their prices and their feature entitlements.

Tenant data (organizations, users, records, subscriptions, transactions, …)
is never touched here — it's user-generated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from talk2record.ai.models import AIModel
from talk2record.ai.models import AIProvider
from talk2record.ai.models import AISettings
from talk2record.ai.models import AITaskBinding
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.services import LegalAcceptanceService
from talk2record.seed.constants import AI_MODEL_CATALOG
from talk2record.seed.constants import AI_PROVIDER_DEFINITIONS
from talk2record.seed.constants import AI_TASK_BINDING_DEFINITIONS
from talk2record.seed.constants import INTEGRATION_DEFINITIONS
from talk2record.seed.constants import PLAN_DEFINITIONS
from talk2record.seed.taxonomy_seed import CATEGORY_DEFINITIONS
from talk2record.seed.taxonomy_seed import DICTIONARY_DEFINITIONS
from talk2record.seed.taxonomy_seed import INDUSTRY_DEFINITIONS
from talk2record.seed.taxonomy_seed import PROCESSING_RULE_DEFINITIONS
from talk2record.seed.taxonomy_seed import PROMPT_DEFINITIONS
from talk2record.seed.taxonomy_seed import SCHEMA_DEFINITIONS
from talk2record.taxonomy.models import Category
from talk2record.taxonomy.models import DomainDictionary
from talk2record.taxonomy.models import ExtractionSchema
from talk2record.taxonomy.models import Industry
from talk2record.taxonomy.models import ProcessingRule
from talk2record.taxonomy.models import PromptTemplate
from talk2record.whatsapp.models import WhatsAppSettings

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ReferenceData:
    legal_versions: dict[str, LegalDocumentVersion]
    plans: dict[str, Plan]


def sync_reference_data(summary) -> ReferenceData:
    legal_versions = _sync_legal_documents(summary)
    plans = _sync_plans(summary)
    _sync_integrations(summary)
    _sync_ai_models(summary)
    _sync_ai_providers(summary)
    _sync_ai_task_bindings(summary)
    _sync_taxonomy(summary)
    return ReferenceData(legal_versions=legal_versions, plans=plans)


def _sync_legal_documents(summary) -> dict[str, LegalDocumentVersion]:
    existing = LegalDocumentVersion.objects.count()
    LegalAcceptanceService.sync_default_versions()
    versions = LegalAcceptanceService.get_active_versions()
    delta = LegalDocumentVersion.objects.count() - existing
    if delta > 0:
        summary.bump("legal_versions", created=delta)
    return versions


def _sync_plans(summary) -> dict[str, Plan]:
    plans: dict[str, Plan] = {}
    for definition in PLAN_DEFINITIONS:
        plan, plan_created = Plan.objects.update_or_create(
            code=definition["code"],
            defaults={
                "name": definition["name"],
                "base_price": definition["base_price"],
                "currency": definition["currency"],
                "region": definition["region"],
                "features": list(definition["features"]),
                "is_active": True,
            },
        )
        summary.bump("plans", created=plan_created, updated=not plan_created)
        plans[plan.code] = plan

        for price in definition.get("prices", ()):
            _, price_created = PlanPrice.objects.update_or_create(
                plan=plan,
                interval=price["interval"],
                currency=price["currency"],
                defaults={
                    "amount": price["amount"],
                    "billing_cycle": dict(price.get("billing_cycle") or {}),
                    "trial_period": dict(price.get("trial_period") or {}),
                    "active": price.get("active", True),
                },
            )
            summary.bump(
                "plan_prices",
                created=price_created,
                updated=not price_created,
            )

        for entitlement in definition.get("entitlements", ()):
            _, entitlement_created = PlanEntitlement.objects.update_or_create(
                plan=plan,
                feature_key=entitlement["feature_key"],
                defaults={
                    "enabled": entitlement.get("enabled", True),
                    "limit": entitlement.get("limit", 0),
                    "period": entitlement.get("period", PlanEntitlement.Period.NONE),
                },
            )
            summary.bump(
                "plan_entitlements",
                created=entitlement_created,
                updated=not entitlement_created,
            )

    return plans


def _sync_integrations(summary) -> None:  # noqa: C901
    """Ensure the integration singletons exist.

    Only structural fields (``enabled``, baseline ``config``) are seeded.
    Secrets and tenant-specific configuration are deliberately **not** filled
    in — they must be entered through Django admin. Existing values for
    ``config`` and credentials are preserved on re-runs.
    """

    for definition in INTEGRATION_DEFINITIONS:
        slug = definition["slug"]
        config = dict(definition.get("config") or {})

        if slug == "whatsapp":
            _upsert_singleton(
                model=WhatsAppSettings,
                summary=summary,
                config=config,
                create_defaults={
                    "enabled": True,
                    "config": config,
                    "encrypted_credential": "",
                },
            )

        elif slug == "paddle":
            _upsert_singleton(
                model=PaddleSettings,
                summary=summary,
                config=config,
                create_defaults={
                    "enabled": True,
                    "environment": PaddleSettings.Environment.SANDBOX,
                    "default_payment_link": "http://localhost:3000/checkout",
                    "default_success_url": (
                        "http://localhost:3000/dashboard/billing?checkout=success"
                    ),
                    "client_side_token": "test_682f6606c513770393dc78e0b1a",
                    "config": config,
                    "encrypted_api_key": "",
                    "encrypted_webhook_secret": "",
                },
            )
            paddle = PaddleSettings.objects.get(pk=1)
            paddle_updates: list[str] = []
            if not paddle.default_payment_link:
                paddle.default_payment_link = "http://localhost:3000/checkout"
                paddle_updates.append("default_payment_link")
            if not paddle.default_success_url:
                paddle.default_success_url = (
                    "http://localhost:3000/dashboard/billing?checkout=success"
                )
                paddle_updates.append("default_success_url")
            if not paddle.client_side_token:
                paddle.client_side_token = "test_682f6606c513770393dc78e0b1a"  # noqa: S105
                paddle_updates.append("client_side_token")
            if paddle_updates:
                paddle_updates.append("updated_at")
                paddle.save(update_fields=paddle_updates)
                summary.bump("integration_singletons", updated=True)

        elif slug == "ai":
            obj, created = AISettings.objects.get_or_create(
                pk=1,
                defaults={"enabled": True},
            )
            if created:
                summary.bump("integration_singletons", created=True)
            elif not obj.enabled:
                obj.enabled = True
                obj.save(update_fields=["enabled", "updated_at"])
                summary.bump("integration_singletons", updated=True)


def _upsert_singleton(*, model, summary, config: dict, create_defaults: dict) -> None:
    obj, created = model.objects.get_or_create(pk=1, defaults=create_defaults)
    if created:
        summary.bump("integration_singletons", created=True)
        return

    updated_fields: list[str] = []
    if not obj.enabled:
        obj.enabled = True
        updated_fields.append("enabled")
    # Only fill in the seed config when the admin hasn't already populated it.
    if not obj.config:
        obj.config = config
        updated_fields.append("config")
    if updated_fields:
        updated_fields.append("updated_at")
        obj.save(update_fields=updated_fields)
        summary.bump("integration_singletons", updated=True)


def _sync_ai_models(summary) -> None:
    """Refresh the curated :class:`AIModel` catalog rows.

    These are pure reference data; ``display_name``, ``capabilities`` and
    ``context_window`` are kept up to date with the seed definitions on every
    run.
    """

    for definition in AI_MODEL_CATALOG:
        _, created = AIModel.objects.update_or_create(
            provider=definition["provider"],
            model_id=definition["model_id"],
            defaults={
                "display_name": definition.get("display_name", ""),
                "capabilities": list(definition.get("capabilities", []) or []),
                "context_window": int(definition.get("context_window", 0) or 0),
                "active": True,
            },
        )
        summary.bump("ai_models", created=created, updated=not created)


def _sync_ai_providers(summary) -> None:
    """Provision baseline :class:`AIProvider` rows without credentials.

    Idempotent and admin-friendly:

    * A row is only created when no row with the same ``name`` exists.
    * Existing rows are never overwritten -- secrets, custom models, and the
      ``is_active`` flag set by an operator survive re-runs.
    * On a fresh database the first seed row per category is marked active so
      the resolver can pick it up immediately. If a different row already
      occupies that category, the new seed row is created inactive so it
      never displaces the operator's choice.
    """

    for definition in AI_PROVIDER_DEFINITIONS:
        if AIProvider.objects.filter(name=definition["name"]).exists():
            continue

        category = definition["category"]
        category_has_active = AIProvider.objects.filter(
            category=category,
            is_active=True,
        ).exists()

        AIProvider.objects.create(
            name=definition["name"],
            slug=definition["slug"],
            category=category,
            display_name=definition.get("display_name", ""),
            base_url=definition.get("base_url", ""),
            models_available=list(definition.get("models_available", []) or []),
            default_model=definition.get("default_model", ""),
            extra_config=dict(definition.get("extra_config", {}) or {}),
            is_active=not category_has_active,
        )
        summary.bump("ai_providers", created=True)


def _sync_ai_task_bindings(summary) -> None:
    """Provision default :class:`AITaskBinding` rows.

    Each binding is created only when the task does not yet have one, so any
    admin override is preserved on re-runs. Bindings whose target model is
    not in the active provider's ``models_available`` are skipped silently
    (validated by ``AITaskBinding.clean()`` on save) so a partial AI setup
    never aborts the seed.
    """

    for definition in AI_TASK_BINDING_DEFINITIONS:
        task = definition["task"]
        if AITaskBinding.objects.filter(task=task).exists():
            continue
        try:
            AITaskBinding.objects.create(
                task=task,
                category=definition["category"],
                model=definition["model"],
            )
        except Exception as exc:  # noqa: BLE001 - validation failures are non-fatal here.
            logger.debug("Skipped AI task binding %s: %s", task, exc)
            continue
        summary.bump("ai_task_bindings", created=True)


# -- Taxonomy seed section --


def _sync_taxonomy(summary) -> None:
    """Provision the dynamic extraction taxonomy.

    Upsert policy:

    * :class:`Industry` and :class:`Category`: ``update_or_create`` on slug —
      the seed *is* the source of truth for the shipped name/description and
      keeps admin tweaks to ``enabled``/``priority`` only.
    * :class:`ExtractionSchema`: ``update_or_create`` on ``(category, name,
      version)`` — bumping the version in code creates a new row; existing
      versions are refreshed in place to match the shipped schema.
    * :class:`PromptTemplate`: **create-if-missing only** on ``(industry,
      category, purpose, version)`` so any prompt edit in admin survives
      re-seeding. Bump the ``version`` in code to ship a new prompt.
    * :class:`DomainDictionary` and :class:`ProcessingRule`: create-if-missing
      on natural keys.
    """

    industries = _sync_industries(summary)
    categories = _sync_categories(summary, industries)
    _sync_schemas(summary, categories)
    _sync_prompts(summary, industries, categories)
    _sync_dictionary(summary, industries, categories)
    _sync_processing_rules(summary, industries, categories)


def _sync_industries(summary) -> dict[str, Industry]:
    industries: dict[str, Industry] = {}
    for definition in INDUSTRY_DEFINITIONS:
        obj, created = Industry.objects.update_or_create(
            slug=definition["slug"],
            defaults={
                "name": definition["name"],
                "description": definition.get("description", ""),
                "priority": definition.get("priority", 100),
            },
        )
        summary.bump("industries", created=created, updated=not created)
        industries[obj.slug] = obj
    return industries


def _sync_categories(
    summary,
    industries: dict[str, Industry],
) -> dict[tuple[str, str], Category]:
    categories: dict[tuple[str, str], Category] = {}
    for definition in CATEGORY_DEFINITIONS:
        industry = industries.get(definition["industry"])
        if industry is None:
            continue
        obj, created = Category.objects.update_or_create(
            industry=industry,
            slug=definition["slug"],
            defaults={
                "name": definition["name"],
                "description": definition.get("description", ""),
                "priority": definition.get("priority", 100),
            },
        )
        summary.bump("taxonomy_categories", created=created, updated=not created)
        categories[(industry.slug, obj.slug)] = obj
    return categories


def _sync_schemas(summary, categories: dict[tuple[str, str], Category]) -> None:
    for definition in SCHEMA_DEFINITIONS:
        category = categories.get(definition["category"])
        if category is None:
            continue
        is_default = definition.get("is_default", False)
        defaults = {
            "json_schema": dict(definition.get("json_schema") or {}),
            "required_fields": list(definition.get("required_fields") or []),
            "is_default": is_default,
        }
        # The unique constraint on (category, is_default=True) means we must
        # clear any prior default before promoting a new schema. Only do this
        # when we are about to set is_default=True on a different row.
        if is_default:
            ExtractionSchema.objects.filter(
                category=category,
                is_default=True,
            ).exclude(name=definition["name"], version=definition["version"]).update(
                is_default=False,
            )

        obj, created = ExtractionSchema.objects.update_or_create(
            category=category,
            name=definition["name"],
            version=definition["version"],
            defaults=defaults,
        )
        summary.bump("extraction_schemas", created=created, updated=not created)
        del obj


def _sync_prompts(
    summary,
    industries: dict[str, Industry],
    categories: dict[tuple[str, str], Category],
) -> None:
    for definition in PROMPT_DEFINITIONS:
        industry_slug = definition.get("industry")
        category_slug = definition.get("category")
        purpose = definition["purpose"]
        version = definition["version"]

        industry = industries.get(industry_slug) if industry_slug else None
        category = None
        if category_slug:
            scope_industry_slug = industry_slug
            if scope_industry_slug is None:
                # category_slug without industry is ambiguous; skip silently.
                continue
            category = categories.get((scope_industry_slug, category_slug))
            if category is None:
                continue

        exists = PromptTemplate.objects.filter(
            industry=industry,
            category=category,
            purpose=purpose,
            version=version,
        ).exists()
        if exists:
            continue

        PromptTemplate.objects.create(
            industry=industry,
            category=category,
            purpose=purpose,
            title=definition.get("title", ""),
            version=version,
            system_prompt=definition.get("system_prompt", ""),
            user_prompt=definition.get("user_prompt", ""),
            example_input=definition.get("example_input", ""),
            example_output=definition.get("example_output", ""),
            enabled=definition.get("enabled", True),
        )
        summary.bump("prompt_templates", created=True)


def _sync_dictionary(
    summary,
    industries: dict[str, Industry],
    categories: dict[tuple[str, str], Category],
) -> None:
    for definition in DICTIONARY_DEFINITIONS:
        industry_slug = definition.get("industry")
        category_slug = definition.get("category")
        industry = industries.get(industry_slug) if industry_slug else None
        category = None
        if category_slug and industry_slug:
            category = categories.get((industry_slug, category_slug))

        _, created = DomainDictionary.objects.get_or_create(
            industry=industry,
            category=category,
            term=definition["term"],
            defaults={
                "normalized_term": definition["normalized_term"],
                "description": definition.get("description", ""),
            },
        )
        summary.bump("dictionary_entries", created=created)


def _sync_processing_rules(
    summary,
    industries: dict[str, Industry],
    categories: dict[tuple[str, str], Category],
) -> None:
    for definition in PROCESSING_RULE_DEFINITIONS:
        industry_slug = definition.get("industry")
        category_slug = definition.get("category")
        industry = industries.get(industry_slug) if industry_slug else None
        if industry is None:
            continue
        category = None
        if category_slug:
            category = categories.get((industry_slug, category_slug))

        # Natural identity for a rule is (industry, category, rule_type,
        # priority) — repeated rule_type rows are allowed when their priority
        # differs (e.g. keyword_match + regex_match for excavation).
        _, created = ProcessingRule.objects.get_or_create(
            industry=industry,
            category=category,
            rule_type=definition["rule_type"],
            priority=definition.get("priority", 100),
            defaults={
                "rule_config": dict(definition.get("rule_config") or {}),
            },
        )
        summary.bump("processing_rules", created=created)
