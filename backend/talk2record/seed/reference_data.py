from __future__ import annotations

from dataclasses import dataclass

from talk2record.ai.models import AISettings
from talk2record.billing.models import Plan
from talk2record.billing.models import StripeSettings
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
    existing_legal_count = LegalDocumentVersion.objects.count()
    LegalAcceptanceService.sync_default_versions()
    legal_versions = LegalAcceptanceService.get_active_versions()
    current_legal_count = LegalDocumentVersion.objects.count()
    if current_legal_count > existing_legal_count:
        summary.bump(
            "legal_versions",
            created=current_legal_count - existing_legal_count,
        )

    plans: dict[str, Plan] = {}
    for plan_definition in PLAN_DEFINITIONS:
        plan, created = Plan.objects.update_or_create(
            code=plan_definition["code"],
            defaults={
                "name": plan_definition["name"],
                "base_price": plan_definition["base_price"],
                "currency": plan_definition["currency"],
                "region": plan_definition["region"],
                "features": list(plan_definition["features"]),
                "is_active": True,
            },
        )
        summary.bump("plans", created=created, updated=not created)
        plans[plan.code] = plan

    for integration_definition in INTEGRATION_DEFINITIONS:
        slug = integration_definition["slug"]
        cfg = dict(integration_definition["config"])
        if slug == "whatsapp":
            _, created = WhatsAppSettings.objects.update_or_create(
                pk=1,
                defaults={"enabled": True, "config": cfg},
            )
            summary.bump("integration_catalog", created=created, updated=not created)
        elif slug == "stripe":
            _, created = StripeSettings.objects.update_or_create(
                pk=1,
                defaults={"enabled": True, "config": cfg},
            )
            summary.bump("integration_catalog", created=created, updated=not created)
        elif slug == "ai":
            _, created = AISettings.objects.update_or_create(
                pk=1,
                defaults={"enabled": True, "config": cfg},
            )
            summary.bump("integration_catalog", created=created, updated=not created)

    return ReferenceData(
        legal_versions=legal_versions,
        plans=plans,
    )
