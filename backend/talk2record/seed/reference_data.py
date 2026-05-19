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
from talk2record.whatsapp.models import WhatsAppSettings


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


def _sync_integrations(summary) -> None:
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
                paddle.client_side_token = "test_682f6606c513770393dc78e0b1a"
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
        except Exception:  # noqa: BLE001 - validation failures are non-fatal here.
            continue
        summary.bump("ai_task_bindings", created=True)
