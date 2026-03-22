from __future__ import annotations

from django.core.management import call_command

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration
from talk2record.integrations.models import WhatsAppInboundRoute
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.seed.constants import INTEGRATION_DEFINITIONS
from talk2record.seed.constants import PLAN_DEFINITIONS
from talk2record.seed.time_range import SeedTimeRange
from talk2record.users.models import User

EXPECTED_ORGANIZATIONS = 2
EXPECTED_USERS = 6
EXPECTED_INTEGRATIONS = len(INTEGRATION_DEFINITIONS)
EXPECTED_PLANS = len(PLAN_DEFINITIONS)


def _model_counts() -> dict[str, int]:
    return {
        "plans": Plan.objects.count(),
        "integrations": Integration.objects.count(),
        "organizations": Organization.objects.count(),
        "users": User.objects.count(),
        "memberships": Membership.objects.count(),
        "subscriptions": Subscription.objects.count(),
        "transactions": Transaction.objects.count(),
        "whatsapp_routes": WhatsAppInboundRoute.objects.count(),
        "api_credentials": ApiCredential.objects.count(),
        "records": Record.objects.count(),
        "daily_metrics": DailyMetric.objects.count(),
        "events": Event.objects.count(),
        "audit_logs": AuditLog.objects.count(),
        "legal_versions": LegalDocumentVersion.objects.count(),
        "legal_acceptances": UserLegalAcceptance.objects.count(),
        "legal_attestations": UserLegalAttestation.objects.count(),
    }


def test_seed_data_command_is_idempotent(db) -> None:
    options = {
        "days": 3,
        "months": 0,
        "years": 0,
        "orgs": EXPECTED_ORGANIZATIONS,
        "users_per_org": 3,
        "records_per_day": 2,
        "password": "SeedDemo123!",
    }
    time_range = SeedTimeRange.from_lookback(
        days=options["days"],
        months=options["months"],
        years=options["years"],
    )
    expected_records = (
        time_range.total_days * options["orgs"] * options["records_per_day"]
    )
    expected_daily_metrics = time_range.total_days * options["orgs"]

    call_command("seed_data", **options)
    first_counts = _model_counts()

    assert first_counts["plans"] >= EXPECTED_PLANS
    assert first_counts["integrations"] >= EXPECTED_INTEGRATIONS
    assert first_counts["organizations"] == EXPECTED_ORGANIZATIONS
    assert first_counts["users"] == EXPECTED_USERS
    assert first_counts["records"] == expected_records
    assert first_counts["daily_metrics"] == expected_daily_metrics
    assert first_counts["events"] > 0
    assert first_counts["audit_logs"] > 0

    call_command("seed_data", **options)
    second_counts = _model_counts()

    assert first_counts == second_counts
    assert Organization.objects.filter(slug="seed-org-001").exists()
    assert Plan.objects.filter(code="growth").exists()
