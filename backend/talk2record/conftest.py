import uuid
from datetime import date
from datetime import datetime
from datetime import timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.utils import timezone

from talk2record.analytics.models import DailyMetric
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.core.vault import SecretVault
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppSettings
from talk2record.legal.services import LegalAcceptanceService
from talk2record.notifications.models import Notification
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
        provider_subscription_id="sub_growth_test",
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
def integration(db) -> WhatsAppSettings:
    s = WhatsAppSettings.get_solo()
    s.enabled = True
    s.config = {"verify_token": "verify-me"}
    s.encrypted_credential = SecretVault.encrypt("supersecret1234")
    s.save(update_fields=["enabled", "config", "encrypted_credential", "updated_at"])
    return s


@pytest.fixture
def api_credential(integration: WhatsAppSettings) -> WhatsAppSettings:
    return integration


@pytest.fixture
def whatsapp_route(organization: Organization) -> WhatsAppInboundRoute:
    return WhatsAppInboundRoute.objects.create(
        organization=organization,
        phone_number_id="123456789",
    )


@pytest.fixture
def record(organization: Organization, workspace_user: User) -> Record:
    return Record.objects.create(
        organization=organization,
        created_by=workspace_user,
        source=Record.Source.WHATSAPP,
        type=Record.Type.VOICE_NOTE,
        audio_url="https://example.com/audio/fixture.ogg",
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


@pytest.fixture
def notification(workspace_user: User, organization: Organization) -> Notification:
    with patch("talk2record.notifications.services._send_notification_to_user"):
        return Notification.objects.create(
            user=workspace_user,
            organization=organization,
            type=Notification.Type.RECORD_STORED,
            title="Test notification",
            message="Your record has been processed.",
            link_url="/dashboard/records",
        )


@pytest.fixture
def domain_event(organization: Organization) -> DomainEventRecord:
    event_id = str(uuid.uuid4())
    return DomainEventRecord.objects.create(
        id=event_id,
        name="record.stored",
        organization_id=organization.pk,
        user_id=None,
        resource_type="record",
        resource_id="1",
        payload={"event_id": event_id, "name": "record.stored"},
        occurred_at=datetime.now(tz=dt_timezone.utc),
        processed=False,
    )
