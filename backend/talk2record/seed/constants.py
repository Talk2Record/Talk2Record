"""Static seed definitions.

Seeding is intentionally narrow: it only provisions **platform / admin**
records that staff would otherwise have to create by hand on every fresh
install — legal documents, integration singletons, billing plans, prices and
entitlements. Tenant data (organizations, users, records, subscriptions,
transactions …) is **not** seeded — that's user-generated.
"""

from __future__ import annotations

from decimal import Decimal

SEED_NAMESPACE = "talk2record.seed"


# ---------------------------------------------------------------------------
# Plans + Prices + Entitlements
# ---------------------------------------------------------------------------

TRIAL_14_DAYS = {"interval": "day", "frequency": 14}

PLAN_DEFINITIONS: tuple[dict, ...] = (
    {
        "code": "starter",
        "name": "Starter",
        "base_price": Decimal("19.00"),
        "currency": "USD",
        "region": "Global",
        "features": [
            "basic-capture",
            "billing-portal",
            "email-support",
        ],
        "prices": (
            {
                "interval": "month",
                "amount": Decimal("19.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "month", "frequency": 1},
                "trial_period": TRIAL_14_DAYS,
            },
            {
                "interval": "year",
                "amount": Decimal("190.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "year", "frequency": 1},
            },
        ),
        "entitlements": (
            {
                "feature_key": "ai.usage",
                "enabled": True,
                "limit": 300,
                "period": "monthly",
            },
            {
                "feature_key": "team.seats",
                "enabled": True,
                "limit": 1,
                "period": "none",
            },
            {
                "feature_key": "api.access",
                "enabled": False,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.basic",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.advanced",
                "enabled": False,
                "limit": 0,
                "period": "none",
            },
        ),
    },
    {
        "code": "growth",
        "name": "Growth",
        "base_price": Decimal("49.00"),
        "currency": "USD",
        "region": "Global",
        "features": [
            "basic-capture",
            "team-workflows",
            "analytics",
            "billing-portal",
            "priority-email-support",
        ],
        "prices": (
            {
                "interval": "month",
                "amount": Decimal("49.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "month", "frequency": 1},
                "trial_period": TRIAL_14_DAYS,
            },
            {
                "interval": "year",
                "amount": Decimal("490.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "year", "frequency": 1},
            },
        ),
        "entitlements": (
            {
                "feature_key": "ai.usage",
                "enabled": True,
                "limit": 1500,
                "period": "monthly",
            },
            {
                "feature_key": "team.seats",
                "enabled": True,
                "limit": 5,
                "period": "none",
            },
            {
                "feature_key": "api.access",
                "enabled": False,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.basic",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.advanced",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
        ),
    },
    {
        "code": "scale",
        "name": "Scale",
        "base_price": Decimal("99.00"),
        "currency": "USD",
        "region": "Global",
        "features": [
            "basic-capture",
            "team-workflows",
            "advanced-analytics",
            "api-access",
            "integrations",
            "priority-support",
        ],
        "prices": (
            {
                "interval": "month",
                "amount": Decimal("99.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "month", "frequency": 1},
            },
            {
                "interval": "year",
                "amount": Decimal("990.00"),
                "currency": "USD",
                "billing_cycle": {"interval": "year", "frequency": 1},
            },
        ),
        "entitlements": (
            {
                "feature_key": "ai.usage",
                "enabled": True,
                "limit": 10000,
                "period": "monthly",
            },
            {
                "feature_key": "team.seats",
                "enabled": True,
                "limit": 25,
                "period": "none",
            },
            {
                "feature_key": "api.access",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.basic",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
            {
                "feature_key": "analytics.advanced",
                "enabled": True,
                "limit": 0,
                "period": "none",
            },
        ),
    },
)


# ---------------------------------------------------------------------------
# Integration singletons
# ---------------------------------------------------------------------------

INTEGRATION_DEFINITIONS: tuple[dict, ...] = (
    {
        "slug": "whatsapp",
        "config": {
            "verify_token": "seed-whatsapp-verify-token",
            "graph_api_version": "v21.0",
            "phone_number_id": "seed-phone-number-id",
            "waba_id": "seed-waba-id",
        },
    },
    {
        "slug": "paddle",
        "config": {"provider": "paddle"},
    },
    {
        "slug": "ai",
        "config": {"provider": "mock"},
    },
)


# ---------------------------------------------------------------------------
# AI provider configuration (global)
# ---------------------------------------------------------------------------

# Seeded :class:`talk2record.ai.models.AIProvider` rows. Credentials are NOT
# included -- staff add the API key in Django admin after seeding. Each row
# represents a sensible default per category; on a fresh install the first
# seeded provider per category becomes ``is_active=True``. On re-runs a row
# is only created when its ``name`` does not already exist, so admin tweaks
# (different default model, additional providers, deactivation, ...) are
# preserved.
AI_PROVIDER_DEFINITIONS: tuple[dict, ...] = (
    {
        "name": "OpenRouter",
        "slug": "openrouter",
        "category": "chat",
        "display_name": "OpenRouter",
        "base_url": "",
        "models_available": [
            "openai/gpt-4o-mini",
            "openrouter/auto",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.0-flash-001",
        ],
        "default_model": "openai/gpt-4o-mini",
    },
    {
        "name": "OpenAI Whisper",
        "slug": "openai",
        "category": "transcription",
        "display_name": "OpenAI Whisper",
        "base_url": "",
        "models_available": ["whisper-1"],
        "default_model": "whisper-1",
    },
)


# Seeded :class:`talk2record.ai.models.AITaskBinding` rows. Each task is
# created only when no binding for that task already exists, so any admin
# overrides made through the UI survive re-runs.
AI_TASK_BINDING_DEFINITIONS: tuple[dict, ...] = (
    {
        "task": "extraction",
        "category": "chat",
        "model": "openai/gpt-4o-mini",
    },
    {
        "task": "summarization",
        "category": "chat",
        "model": "openai/gpt-4o-mini",
    },
    {
        "task": "chat",
        "category": "chat",
        "model": "openai/gpt-4o-mini",
    },
    {
        "task": "transcription",
        "category": "transcription",
        "model": "whisper-1",
    },
)


# Curated catalog rows for :class:`talk2record.ai.models.AIModel`. These are
# pure reference data and are refreshed on every seed run.
AI_MODEL_CATALOG: tuple[dict, ...] = (
    {
        "provider": "openrouter",
        "model_id": "openai/gpt-4o-mini",
        "display_name": "GPT-4o mini (via OpenRouter)",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    {
        "provider": "openrouter",
        "model_id": "openrouter/auto",
        "display_name": "OpenRouter auto-route",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    {
        "provider": "openrouter",
        "model_id": "anthropic/claude-3.5-sonnet",
        "display_name": "Claude 3.5 Sonnet (via OpenRouter)",
        "capabilities": ["chat", "vision"],
        "context_window": 200000,
    },
    {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "display_name": "GPT-4o mini",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    {
        "provider": "openai",
        "model_id": "gpt-4o",
        "display_name": "GPT-4o",
        "capabilities": ["chat", "vision"],
        "context_window": 128000,
    },
    {
        "provider": "openai",
        "model_id": "whisper-1",
        "display_name": "Whisper",
        "capabilities": ["transcription"],
        "context_window": 0,
    },
    {
        "provider": "groq",
        "model_id": "llama-3.3-70b-versatile",
        "display_name": "Llama 3.3 70B Versatile",
        "capabilities": ["chat"],
        "context_window": 128000,
    },
    {
        "provider": "anthropic",
        "model_id": "claude-3-5-sonnet-20241022",
        "display_name": "Claude 3.5 Sonnet",
        "capabilities": ["chat", "vision"],
        "context_window": 200000,
    },
)
