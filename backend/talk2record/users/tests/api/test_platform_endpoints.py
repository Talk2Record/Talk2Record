from __future__ import annotations

from datetime import date
from datetime import timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.analytics.models import DailyMetric
from talk2record.audit.models import AuditLog
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.core.vault import SecretVault
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def workspace_user(db) -> User:
    user = UserFactory.create()
    organization = Organization.objects.create(
        name="Acme Workspace",
        slug="acme-workspace",
    )
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
def authed_client(api_client: APIClient, workspace_user: User) -> APIClient:
    api_client.force_authenticate(user=workspace_user)
    return api_client


@pytest.fixture
def legal_versions(db) -> dict[str, LegalDocumentVersion]:
    LegalAcceptanceService.sync_default_versions()
    return {
        version.document_key: version for version in LegalDocumentVersion.objects.all()
    }


@pytest.fixture
def subscription(workspace_user: User) -> Subscription:
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
    subscription = Subscription.objects.create(
        organization=workspace_user.current_organization,
        plan=plan,
        provider_subscription_id="sub_platform_test",
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
def record(workspace_user: User) -> Record:
    return Record.objects.create(
        organization=workspace_user.current_organization,
        created_by=workspace_user,
        source=Record.Source.WHATSAPP,
        type=Record.Type.VOICE_NOTE,
        audio_url="https://example.com/audio/fixture.ogg",
    )


@pytest.fixture
def daily_metric(workspace_user: User) -> DailyMetric:
    return DailyMetric.objects.create(
        organization=workspace_user.current_organization,
        metric_date=date.today(),
        voice_processed=10,
        records_created=8,
        revenue=Decimal("900.00"),
        feature_usage=5,
        active_users=3,
    )


@pytest.fixture
def global_paddle_settings() -> PaddleSettings:
    s = PaddleSettings.get_solo()
    s.enabled = True
    s.environment = PaddleSettings.Environment.SANDBOX
    s.encrypted_api_key = SecretVault.encrypt("pdl_test_secret")
    s.encrypted_webhook_secret = SecretVault.encrypt("whsec_test")
    s.save(
        update_fields=[
            "enabled",
            "environment",
            "encrypted_api_key",
            "encrypted_webhook_secret",
            "updated_at",
        ],
    )
    return s


@pytest.mark.django_db
class TestPlatformEndpoints:
    def test_organizations_list(self, authed_client: APIClient, workspace_user: User):
        response = authed_client.get(reverse("api:organization-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["name"] == workspace_user.current_organization.name

    def test_memberships_list(self, authed_client: APIClient):
        response = authed_client.get(reverse("api:membership-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["role"] == Membership.Role.OWNER

    def test_records_list_and_create(
        self,
        authed_client: APIClient,
        workspace_user: User,
        record: Record,
    ):
        list_response = authed_client.get(reverse("api:record-list"))

        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data[0]["source"] == record.source

    def test_subscriptions_list(
        self,
        authed_client: APIClient,
        subscription: Subscription,
    ):
        response = authed_client.get(reverse("api:subscription-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["plan"] == subscription.plan.name
        assert len(response.data[0]["invoices"]) == 1

    def test_billing_checkout_requires_acceptance(
        self,
        authed_client: APIClient,
        subscription: Subscription,
        global_paddle_settings: PaddleSettings,
    ):
        assert global_paddle_settings.enabled
        response = authed_client.post(
            reverse("api:billing-checkout"),
            {"plan": subscription.plan.code, "acceptedBillingTerms": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_billing_checkout_records_acceptance_and_audit(
        self,
        authed_client: APIClient,
        workspace_user: User,
        subscription: Subscription,
        legal_versions: dict[str, LegalDocumentVersion],
        global_paddle_settings: PaddleSettings,
    ):
        from talk2record.billing.models import PlanPrice

        PlanPrice.objects.create(
            plan=subscription.plan,
            paddle_price_id="pri_growth_checkout",
            interval="month",
            amount=Decimal("49.00"),
            currency="USD",
        )
        assert global_paddle_settings.enabled
        fake_response = MagicMock()
        fake_response.status_code = 201
        fake_response.content = b"{}"
        fake_response.text = ""
        fake_response.json.return_value = {
            "data": {"checkout": {"url": "https://pay.paddle.com/checkout/123"}},
        }
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=fake_response,
        ):
            response = authed_client.post(
                reverse("api:billing-checkout"),
                {"plan": subscription.plan.code, "acceptedBillingTerms": True},
                format="json",
            )

        assert response.status_code == status.HTTP_200_OK
        assert "checkoutUrl" in response.data
        assert UserLegalAcceptance.objects.filter(
            user=workspace_user,
            document_version=legal_versions[
                LegalDocumentVersion.DocumentKey.BILLING_POLICY
            ],
        ).exists()
        assert UserLegalAttestation.objects.filter(
            user=workspace_user,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context="checkout",
        ).exists()
        assert AuditLog.objects.filter(action="billing.checkout.started").exists()

    def test_billing_webhook(self, api_client: APIClient):
        response = api_client.post(reverse("api-billing-webhook"), format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert AuditLog.objects.filter(
            action="billing.webhook.received",
            resource_id="paddle",
        ).exists()

    def test_legal_documents_and_status(
        self,
        authed_client: APIClient,
        legal_versions: dict[str, LegalDocumentVersion],
    ):
        documents_response = authed_client.get(reverse("api:legal-document-list"))
        status_response = authed_client.get(reverse("api:legal-profile-status"))

        assert documents_response.status_code == status.HTTP_200_OK
        assert len(documents_response.data) == len(legal_versions)
        assert status_response.status_code == status.HTTP_200_OK
        assert (
            LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE
            in status_response.data["required_signup_documents"]
        )

    def test_legal_accept_and_attest(
        self,
        authed_client: APIClient,
        workspace_user: User,
        legal_versions: dict[str, LegalDocumentVersion],
    ):
        accept_response = authed_client.post(
            reverse("api:legal-profile-accept"),
            {
                "document_keys": [LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE],
                "source": UserLegalAcceptance.Source.SETTINGS,
            },
            format="json",
        )
        attest_response = authed_client.post(
            reverse("api:legal-profile-attest"),
            {
                "kind": UserLegalAttestation.Kind.AI_OUTPUT_REVIEW,
                "context": "settings",
                "metadata": {"screen": "settings"},
            },
            format="json",
        )

        assert accept_response.status_code == status.HTTP_200_OK
        assert attest_response.status_code == status.HTTP_201_CREATED
        assert UserLegalAcceptance.objects.filter(
            user=workspace_user,
            document_version=legal_versions[
                LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE
            ],
        ).exists()
        assert UserLegalAttestation.objects.filter(
            user=workspace_user,
            context="settings",
        ).exists()

    def test_analytics_daily_metrics(
        self,
        authed_client: APIClient,
        daily_metric: DailyMetric,
    ):
        response = authed_client.get(reverse("api:daily-metric-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["voice_processed"] == daily_metric.voice_processed
