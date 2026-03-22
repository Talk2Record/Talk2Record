from __future__ import annotations

from decimal import Decimal

SEED_NAMESPACE = "talk2record.seed"
DEFAULT_PASSWORD = "SeedDemo123!"  # noqa: S105
DEFAULT_DAYS = 30
DEFAULT_ORGANIZATION_COUNT = 3
DEFAULT_USERS_PER_ORGANIZATION = 3
DEFAULT_RECORDS_PER_DAY = 2
SEED_IP_ADDRESS = "127.0.0.1"
SEED_USER_AGENT = "talk2record-seed-script/1.0"

PLAN_DEFINITIONS = (
    {
        "code": "starter",
        "name": "Starter",
        "base_price": Decimal("19.00"),
        "currency": "USD",
        "region": "US",
        "features": ["basic-capture", "dashboard"],
    },
    {
        "code": "growth",
        "name": "Growth",
        "base_price": Decimal("49.00"),
        "currency": "USD",
        "region": "US",
        "features": ["team-workflows", "analytics", "audit-logs"],
    },
    {
        "code": "scale",
        "name": "Scale",
        "base_price": Decimal("99.00"),
        "currency": "USD",
        "region": "US",
        "features": ["team-workflows", "analytics", "audit-logs", "integrations"],
    },
)

INTEGRATION_DEFINITIONS = (
    {
        "slug": "whatsapp",
        "config": {"verify_token": "seed-whatsapp-verify-token"},
    },
    {
        "slug": "stripe",
        "config": {"provider": "stripe"},
    },
    {
        "slug": "ai",
        "config": {"provider": "mock"},
    },
)

REGIONS = ("US", "KE", "NG")
TIMEZONES = ("UTC", "Africa/Nairobi", "Africa/Lagos")
PRODUCT_CATALOG = (
    "Bulk Cooking Oil",
    "Premium Rice",
    "Laundry Detergent",
    "Office Paper",
    "Bottled Water",
    "Solar Lamps",
)
CUSTOMER_NAMES = (
    "Acme Traders",
    "Kifaru Stores",
    "Blue River Market",
    "Maua Wholesalers",
    "Savannah Retail",
    "Northwind Supplies",
)
PAYMENT_METHODS = ("cash", "mobile-money", "bank-transfer", "card")
