from __future__ import annotations

import pytest
from django.core.management import call_command

from talk2record.ai.models import AIModel
from talk2record.ai.models import AIProvider
from talk2record.ai.models import AISettings
from talk2record.ai.models import AITaskBinding
from talk2record.analytics.models import DailyMetric
from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.seed.constants import AI_MODEL_CATALOG
from talk2record.seed.constants import AI_PROVIDER_DEFINITIONS
from talk2record.seed.constants import AI_TASK_BINDING_DEFINITIONS
from talk2record.seed.constants import INTEGRATION_DEFINITIONS
from talk2record.seed.constants import PLAN_DEFINITIONS
from talk2record.users.models import User
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppSettings

EXPECTED_PLANS = len(PLAN_DEFINITIONS)
EXPECTED_PRICES = sum(len(plan.get("prices", ())) for plan in PLAN_DEFINITIONS)
EXPECTED_ENTITLEMENTS = sum(
    len(plan.get("entitlements", ())) for plan in PLAN_DEFINITIONS
)
EXPECTED_INTEGRATIONS = len(INTEGRATION_DEFINITIONS)
EXPECTED_AI_PROVIDERS = len(AI_PROVIDER_DEFINITIONS)
EXPECTED_AI_TASK_BINDINGS = len(AI_TASK_BINDING_DEFINITIONS)
EXPECTED_AI_MODELS = len(AI_MODEL_CATALOG)


def _admin_counts() -> dict[str, int]:
    return {
        "plans": Plan.objects.count(),
        "plan_prices": PlanPrice.objects.count(),
        "plan_entitlements": PlanEntitlement.objects.count(),
        "whatsapp_settings": WhatsAppSettings.objects.count(),
        "ai_settings": AISettings.objects.count(),
        "ai_providers": AIProvider.objects.count(),
        "ai_task_bindings": AITaskBinding.objects.count(),
        "ai_models": AIModel.objects.count(),
        "paddle_settings": PaddleSettings.objects.count(),
        "legal_versions": LegalDocumentVersion.objects.count(),
    }


def _tenant_counts() -> dict[str, int]:
    return {
        "organizations": Organization.objects.count(),
        "memberships": Membership.objects.count(),
        "users": User.objects.count(),
        "records": Record.objects.count(),
        "subscriptions": Subscription.objects.count(),
        "transactions": Transaction.objects.count(),
        "whatsapp_routes": WhatsAppInboundRoute.objects.count(),
        "daily_metrics": DailyMetric.objects.count(),
        "events": Event.objects.count(),
        "audit_logs": AuditLog.objects.count(),
        "legal_acceptances": UserLegalAcceptance.objects.count(),
        "legal_attestations": UserLegalAttestation.objects.count(),
    }


@pytest.mark.django_db(transaction=True)
def test_seed_data_provisions_admin_records_only() -> None:
    call_command("seed_data")

    admin = _admin_counts()
    assert admin["plans"] == EXPECTED_PLANS
    assert admin["plan_prices"] == EXPECTED_PRICES
    assert admin["plan_entitlements"] == EXPECTED_ENTITLEMENTS
    assert admin["whatsapp_settings"] == 1
    assert admin["paddle_settings"] == 1
    assert admin["ai_settings"] == 1
    assert admin["ai_providers"] == EXPECTED_AI_PROVIDERS
    assert admin["ai_task_bindings"] == EXPECTED_AI_TASK_BINDINGS
    assert admin["ai_models"] == EXPECTED_AI_MODELS
    assert admin["legal_versions"] >= 1

    # Seeded providers must not include any plaintext credentials.
    for provider in AIProvider.objects.all():
        assert provider.encrypted_credential == ""

    # First seed row per category should be active so the resolver works
    # immediately after seeding (admins still need to add the API key).
    assert AIProvider.objects.filter(category="chat", is_active=True).count() == 1
    assert (
        AIProvider.objects.filter(category="transcription", is_active=True).count()
        == 1
    )

    # Tenant data must never be touched by the seed command.
    assert _tenant_counts() == {
        "organizations": 0,
        "memberships": 0,
        "users": 0,
        "records": 0,
        "subscriptions": 0,
        "transactions": 0,
        "whatsapp_routes": 0,
        "daily_metrics": 0,
        "events": 0,
        "audit_logs": 0,
        "legal_acceptances": 0,
        "legal_attestations": 0,
    }


@pytest.mark.django_db(transaction=True)
def test_seed_data_is_idempotent() -> None:
    call_command("seed_data")
    first = _admin_counts()

    call_command("seed_data")
    second = _admin_counts()

    assert first == second


@pytest.mark.django_db(transaction=True)
def test_seed_data_updates_existing_plans_in_place() -> None:
    call_command("seed_data")
    plan = Plan.objects.get(code="growth")

    plan.name = "Manually renamed"
    plan.is_active = False
    plan.save(update_fields=["name", "is_active"])

    call_command("seed_data")
    plan.refresh_from_db()

    # Seed must reset the plan to its canonical configuration so admins can
    # rely on `seed_data` as a "reset to known state" tool for reference data.
    assert plan.name == "Growth"
    assert plan.is_active is True


@pytest.mark.django_db(transaction=True)
def test_seed_data_preserves_admin_ai_provider_tweaks() -> None:
    call_command("seed_data")

    chat_provider = AIProvider.objects.get(name="OpenRouter")
    chat_provider.encrypted_credential = "preserved-encrypted-key"
    chat_provider.default_model = "openrouter/auto"
    chat_provider.save(
        update_fields=[
            "encrypted_credential",
            "default_model",
            "updated_at",
        ],
    )

    AITaskBinding.objects.filter(task="extraction").update(model="openrouter/auto")

    call_command("seed_data")

    chat_provider.refresh_from_db()
    assert chat_provider.encrypted_credential == "preserved-encrypted-key"
    assert chat_provider.default_model == "openrouter/auto"
    assert AITaskBinding.objects.get(task="extraction").model == "openrouter/auto"


@pytest.mark.django_db(transaction=True)
def test_seed_data_does_not_overwrite_existing_paddle_credentials() -> None:
    call_command("seed_data")

    paddle = PaddleSettings.objects.get(pk=1)
    paddle.encrypted_api_key = "preserved-encrypted-key"
    paddle.encrypted_webhook_secret = "preserved-encrypted-secret"
    paddle.environment = PaddleSettings.Environment.PRODUCTION
    paddle.save(
        update_fields=[
            "encrypted_api_key",
            "encrypted_webhook_secret",
            "environment",
            "updated_at",
        ],
    )

    call_command("seed_data")

    paddle.refresh_from_db()
    assert paddle.encrypted_api_key == "preserved-encrypted-key"
    assert paddle.encrypted_webhook_secret == "preserved-encrypted-secret"
    assert paddle.environment == PaddleSettings.Environment.PRODUCTION
