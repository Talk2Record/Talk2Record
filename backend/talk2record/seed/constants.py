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
