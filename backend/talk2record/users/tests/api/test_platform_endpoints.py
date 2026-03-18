from __future__ import annotations

from datetime import date
from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.analytics.models import DailyMetric
from talk2record.audit.models import AuditLog
from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration
from talk2record.integrations.models import OrganizationIntegration
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
    organization = Organization.objects.create(name="Acme Workspace", slug="acme-workspace")
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
        version.document_key: version
        for version in LegalDocumentVersion.objects.all()
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
def organization_integration(workspace_user: User) -> OrganizationIntegration:
    integration, _ = Integration.objects.get_or_create(
        slug="whatsapp",
        defaults={
            "name": "WhatsApp",
            "type": Integration.Type.WHATSAPP,
            "config_schema": {"requiresEndpoint": True},
        },
    )
    return OrganizationIntegration.objects.create(
        organization=workspace_user.current_organization,
        integration=integration,
        status=OrganizationIntegration.Status.AVAILABLE,
    )


@pytest.fixture
def record(workspace_user: User) -> Record:
    return Record.objects.create(
        organization=workspace_user.current_organization,
        created_by=workspace_user,
        customer_name="Kifaru",
        product="Oil",
        quantity=2,
        amount=Decimal("120.00"),
        currency="USD",
        payment_method="cash",
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

    def test_records_list_and_create(self, authed_client: APIClient, workspace_user: User, record: Record):
        list_response = authed_client.get(reverse("api:record-list"))

        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data[0]["customer_name"] == record.customer_name

        create_response = authed_client.post(
            reverse("api:record-list"),
            {
                "organization": workspace_user.current_organization.pk,
                "source": Record.Source.UPLOAD,
                "customer_name": "Maua Retail",
                "product": "Rice",
                "quantity": 4,
                "amount": "450.00",
                "currency": "USD",
            },
            format="json",
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        assert Record.objects.filter(customer_name="Maua Retail").exists()

    def test_subscriptions_list(self, authed_client: APIClient, subscription: Subscription):
        response = authed_client.get(reverse("api:subscription-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["plan"] == subscription.plan.name
        assert len(response.data[0]["invoices"]) == 1

    def test_billing_checkout_requires_acceptance(self, authed_client: APIClient, subscription: Subscription):
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
            document_version=legal_versions[LegalDocumentVersion.DocumentKey.BILLING_POLICY],
        ).exists()
        assert UserLegalAttestation.objects.filter(
            user=workspace_user,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context="checkout",
        ).exists()
        assert AuditLog.objects.filter(action="billing.checkout.started").exists()

    def test_billing_webhook(self, api_client: APIClient):
        response = api_client.post(reverse("api-billing-webhook", kwargs={"provider": "stripe"}), format="json")

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert AuditLog.objects.filter(action="billing.webhook.received", resource_id="stripe").exists()

    def test_integrations_list(self, authed_client: APIClient, organization_integration: OrganizationIntegration):
        response = authed_client.get(reverse("api:integration-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["id"] == organization_integration.integration.slug

    def test_integration_test_connection_requires_permission(
        self,
        authed_client: APIClient,
        organization_integration: OrganizationIntegration,
    ):
        response = authed_client.post(
            reverse("api:integration-action-test-connection"),
            {"id": organization_integration.integration.slug, "confirmedPermission": False},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_integration_test_connection_updates_state_and_creates_credential(
        self,
        authed_client: APIClient,
        workspace_user: User,
        organization_integration: OrganizationIntegration,
    ):
        response = authed_client.post(
            reverse("api:integration-action-test-connection"),
            {
                "id": organization_integration.integration.slug,
                "endpoint": "https://example.com/hook",
                "secret": "supersecret1234",
                "confirmedPermission": True,
            },
            format="json",
        )

        organization_integration.refresh_from_db()
        assert response.status_code == status.HTTP_200_OK
        assert organization_integration.status == OrganizationIntegration.Status.CONNECTED
        assert organization_integration.endpoint == "https://example.com/hook"
        assert ApiCredential.objects.filter(organization_integration=organization_integration).exists()
        assert UserLegalAttestation.objects.filter(
            user=workspace_user,
            kind=UserLegalAttestation.Kind.WHATSAPP_PERMISSION,
            context="integration-test",
        ).exists()

    def test_legal_documents_and_status(self, authed_client: APIClient, legal_versions: dict[str, LegalDocumentVersion]):
        documents_response = authed_client.get(reverse("api:legal-document-list"))
        status_response = authed_client.get(reverse("api:legal-profile-status"))

        assert documents_response.status_code == status.HTTP_200_OK
        assert len(documents_response.data) == len(legal_versions)
        assert status_response.status_code == status.HTTP_200_OK
        assert LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE in status_response.data["required_signup_documents"]

    def test_legal_accept_and_attest(self, authed_client: APIClient, workspace_user: User, legal_versions: dict[str, LegalDocumentVersion]):
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
            document_version=legal_versions[LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE],
        ).exists()
        assert UserLegalAttestation.objects.filter(user=workspace_user, context="settings").exists()

    def test_analytics_daily_metrics(self, authed_client: APIClient, daily_metric: DailyMetric):
        response = authed_client.get(reverse("api:daily-metric-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]["voice_processed"] == daily_metric.voice_processed
