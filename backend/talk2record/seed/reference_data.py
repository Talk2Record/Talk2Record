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

from talk2record.ai.models import AISettings
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.services import LegalAcceptanceService
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
                    "config": config,
                    "encrypted_api_key": "",
                    "encrypted_webhook_secret": "",
                },
            )

        elif slug == "ai":
            _upsert_singleton(
                model=AISettings,
                summary=summary,
                config=config,
                create_defaults={
                    "enabled": True,
                    "config": config,
                    "encrypted_credential": "",
                },
            )


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
