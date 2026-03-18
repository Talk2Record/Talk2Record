import pytest
from decimal import Decimal
from datetime import date
from datetime import timedelta
from django.utils import timezone

from talk2record.analytics.models import DailyMetric
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.integrations.models import Integration
from talk2record.integrations.models import OrganizationIntegration
from talk2record.legal.services import LegalAcceptanceService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory.create()


@pytest.fixture
def organization(db) -> Organization:
    return Organization.objects.create(name="Acme Workspace", slug="acme-workspace")


@pytest.fixture
def workspace_user(user: User, organization: Organization) -> User:
    Membership.objects.create(
        user=user,
        organization=organization,
        role=Membership.Role.OWNER,
        status=Membership.Status.ACTIVE,
    )
    user.current_organization = organization
    user.save(update_fields=["current_organization"])
    return user


@pytest.fixture
def legal_versions(db):
    LegalAcceptanceService.sync_default_versions()
    return LegalAcceptanceService.get_active_versions()


@pytest.fixture
def plan(db) -> Plan:
    plan, _ = Plan.objects.get_or_create(
        code="growth",
        defaults={
            "name": "Growth",
            "base_price": Decimal("49.00"),
            "currency": "USD",
            "region": "US",
            "features": ["team-workflows"],
        },
    )
    return plan


@pytest.fixture
def subscription(organization: Organization, plan: Plan) -> Subscription:
    subscription = Subscription.objects.create(
        organization=organization,
        plan=plan,
        provider=Subscription.Provider.STRIPE,
        status=Subscription.Status.ACTIVE,
        currency="USD",
        amount=Decimal("49.00"),
        seats=3,
        current_period_end=timezone.now() + timedelta(days=30),
    )
    Transaction.objects.create(
        subscription=subscription,
        provider_transaction_id="txn_1",
        amount=Decimal("49.00"),
        currency="USD",
        status=Transaction.Status.PAID,
        invoice_number="inv_1",
        issued_at=timezone.now(),
        paid_at=timezone.now(),
    )
    return subscription


@pytest.fixture
def integration(db) -> Integration:
    integration, _ = Integration.objects.get_or_create(
        slug="whatsapp",
        defaults={
            "name": "WhatsApp",
            "type": Integration.Type.WHATSAPP,
            "config_schema": {"requiresEndpoint": True},
        },
    )
    return integration


@pytest.fixture
def organization_integration(
    organization: Organization,
    integration: Integration,
) -> OrganizationIntegration:
    return OrganizationIntegration.objects.create(
        organization=organization,
        integration=integration,
        status=OrganizationIntegration.Status.AVAILABLE,
    )


@pytest.fixture
def record(organization: Organization, workspace_user: User) -> Record:
    return Record.objects.create(
        organization=organization,
        created_by=workspace_user,
        customer_name="Kifaru",
        product="Oil",
        quantity=2,
        amount=Decimal("120.00"),
        currency="USD",
        payment_method="cash",
    )


@pytest.fixture
def daily_metric(organization: Organization) -> DailyMetric:
    return DailyMetric.objects.create(
        organization=organization,
        metric_date=date.today(),
        voice_processed=10,
        records_created=8,
        revenue=Decimal("900.00"),
        feature_usage=5,
        active_users=3,
    )
