from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import (
    BillingProviderConfig,
    Plan,
    PlanEntitlement,
    PlanProviderPrice,
    Subscription,
    Transaction,
)
from talk2record.billing.paddle_provider import PaddleBillingProvider
from talk2record.billing.providers import BillingProviderRegistry
from talk2record.core.vault import SecretVault


@pytest.mark.django_db
class TestBillingProviderRegistry:
    def test_paddle_config_returns_paddle_provider(self):
        BillingProviderConfig.objects.create(
            provider="paddle",
            display_name="Paddle",
            enabled=True,
            environment="sandbox",
            encrypted_api_key=SecretVault.encrypt("pdl_live_123"),
            config={"default_price_id": "pri_123"},
        )
        provider = BillingProviderRegistry.get("paddle")
        assert isinstance(provider, PaddleBillingProvider)

    def test_global_provider_prefers_enabled_config(self):
        BillingProviderConfig.objects.create(
            provider="paddle",
            enabled=True,
            encrypted_api_key=SecretVault.encrypt("pdl_api"),
        )
        provider = BillingProviderRegistry.get_global_provider()
        assert isinstance(provider, PaddleBillingProvider)


@pytest.mark.django_db
class TestEntitlements:
    def test_reads_plan_entitlements(self, organization, plan):
        Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider=Subscription.Provider.STRIPE,
            status=Subscription.Status.ACTIVE,
            currency="USD",
            amount=Decimal("49.00"),
            seats=3,
        )
        PlanEntitlement.objects.create(
            plan=plan,
            feature_key="ai.usage",
            enabled=True,
            limit=1000,
            period=PlanEntitlement.Period.MONTHLY,
        )
        PlanEntitlement.objects.create(
            plan=plan,
            feature_key="whatsapp.outbound",
            enabled=True,
        )

        assert EntitlementService.has_feature(organization, "whatsapp.outbound")
        assert EntitlementService.get_limit(organization, "ai.usage") == 1000
        assert not EntitlementService.has_feature(organization, "unknown.feature")

    def test_no_subscription_returns_empty(self, organization):
        assert EntitlementService.list_for_organization(organization) == []


@pytest.mark.django_db
class TestPaddleWebhook:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    @pytest.fixture(autouse=True)
    def _no_real_event_bus(self, settings):
        settings.CELERY_TASK_ALWAYS_EAGER = True
        with patch("talk2record.billing.views.EventBus.publish"):
            yield

    def test_subscription_created_upserts_and_emits_event(
        self,
        api_client: APIClient,
        organization,
        plan,
    ):
        PlanProviderPrice.objects.create(
            plan=plan,
            provider="paddle",
            provider_price_id="pri_growth",
            interval="month",
        )
        payload = {
            "event_type": "subscription.created",
            "data": {
                "id": "sub_001",
                "status": "active",
                "items": [{"price": {"id": "pri_growth"}}],
                "custom_data": {
                    "organization_id": str(organization.pk),
                    "plan_code": plan.code,
                },
            },
        }
        url = reverse("api-billing-webhook", kwargs={"provider": "paddle"})
        response = api_client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 202
        subscription = Subscription.objects.get(provider_subscription_id="sub_001")
        assert subscription.organization_id == organization.pk
        assert subscription.provider == Subscription.Provider.PADDLE

    def test_transaction_completed_records_invoice(
        self,
        api_client: APIClient,
        organization,
        plan,
    ):
        subscription = Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider=Subscription.Provider.PADDLE,
            provider_subscription_id="sub_abc",
            status=Subscription.Status.ACTIVE,
        )
        payload = {
            "event_type": "transaction.completed",
            "data": {
                "id": "txn_1",
                "subscription_id": "sub_abc",
                "currency_code": "USD",
                "details": {"totals": {"grand_total": "4900"}},
                "invoice_number": "INV-0001",
                "billed_at": "2026-02-01T00:00:00Z",
                "custom_data": {"organization_id": str(organization.pk)},
            },
        }
        url = reverse("api-billing-webhook", kwargs={"provider": "paddle"})
        response = api_client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 202
        transaction = Transaction.objects.get(provider_transaction_id="txn_1")
        assert transaction.subscription == subscription
        assert transaction.status == Transaction.Status.PAID
        assert float(transaction.amount) == 49.0

    def test_rejects_invalid_signature_when_secret_configured(
        self,
        api_client: APIClient,
    ):
        BillingProviderConfig.objects.create(
            provider="paddle",
            enabled=True,
            encrypted_webhook_secret=SecretVault.encrypt("sekret"),
        )
        url = reverse("api-billing-webhook", kwargs={"provider": "paddle"})
        response = api_client.post(
            url,
            data=json.dumps({"event_type": "subscription.created", "data": {}}),
            content_type="application/json",
            HTTP_PADDLE_SIGNATURE="ts=123;h1=totally-not-valid",
        )
        assert response.status_code == 400


@pytest.mark.django_db
class TestPaddleProvider:
    def test_create_checkout_uses_plan_price(self, organization, plan):
        PlanProviderPrice.objects.create(
            plan=plan,
            provider="paddle",
            provider_price_id="pri_abc",
            interval="month",
        )
        provider = PaddleBillingProvider(api_key="pdl_key", environment="sandbox")

        fake_response = type(
            "Resp",
            (),
            {
                "status_code": 201,
                "content": b"{}",
                "text": "",
                "json": staticmethod(
                    lambda: {
                        "data": {"checkout": {"url": "https://pay.example/123"}},
                    },
                ),
            },
        )()

        with patch(
            "talk2record.billing.paddle_provider.requests.request",
            return_value=fake_response,
        ) as mock_request:
            session = provider.create_checkout(organization=organization, plan=plan)

        assert session.checkout_url == "https://pay.example/123"
        args, kwargs = mock_request.call_args
        assert kwargs["json"]["items"][0]["price_id"] == "pri_abc"


@pytest.mark.django_db
class TestEntitlementsAPI:
    def test_authenticated_user_sees_entitlements(
        self,
        workspace_user,
        organization,
        plan,
    ):
        Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider=Subscription.Provider.STRIPE,
            status=Subscription.Status.ACTIVE,
        )
        PlanEntitlement.objects.create(
            plan=plan,
            feature_key="ai.usage",
            enabled=True,
            limit=500,
            period=PlanEntitlement.Period.MONTHLY,
        )
        client = APIClient()
        client.force_authenticate(user=workspace_user)
        response = client.get(reverse("api:billing-entitlements"))
        assert response.status_code == 200
        features = {row["feature_key"]: row for row in response.data}
        assert features["ai.usage"]["limit"] == 500
        assert features["ai.usage"]["period"] == "monthly"
