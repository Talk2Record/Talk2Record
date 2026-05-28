from __future__ import annotations

import json
from decimal import Decimal
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.core.vault import SecretVault


def _configure_paddle(env: str = "sandbox") -> PaddleSettings:
    settings = PaddleSettings.get_solo()
    settings.enabled = True
    settings.environment = env
    settings.encrypted_api_key = SecretVault.encrypt("pdl_test_secret")
    settings.encrypted_webhook_secret = SecretVault.encrypt("whsec_test")
    settings.save(
        update_fields=[
            "enabled",
            "environment",
            "encrypted_api_key",
            "encrypted_webhook_secret",
            "updated_at",
        ],
    )
    return settings


@pytest.mark.django_db
class TestEntitlements:
    def test_reads_plan_entitlements(self, organization, plan):
        Subscription.objects.create(
            organization=organization,
            plan=plan,
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
        with patch("talk2record.billing.webhook_pipeline.EventBus.publish"):
            yield

    def test_subscription_created_upserts_and_emits_event(
        self,
        api_client: APIClient,
        organization,
        plan,
    ):
        PlanPrice.objects.create(
            plan=plan,
            paddle_price_id="pri_growth",
            interval="month",
            amount=Decimal("49.00"),
            currency="USD",
        )
        payload = {
            "event_id": "evt_pillar_sub_001",
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
        url = reverse("api-billing-webhook")
        response = api_client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert response.status_code == 202
        subscription = Subscription.objects.get(provider_subscription_id="sub_001")
        assert subscription.organization_id == organization.pk

    def test_transaction_completed_records_invoice(
        self,
        api_client: APIClient,
        organization,
        plan,
    ):
        subscription = Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider_subscription_id="sub_abc",
            status=Subscription.Status.ACTIVE,
        )
        payload = {
            "event_id": "evt_pillar_txn_1",
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
        url = reverse("api-billing-webhook")
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
        _configure_paddle()
        url = reverse("api-billing-webhook")
        response = api_client.post(
            url,
            data=json.dumps({"event_type": "subscription.created", "data": {}}),
            content_type="application/json",
            HTTP_PADDLE_SIGNATURE="ts=123;h1=totally-not-valid",
        )
        assert response.status_code == 400


def _fake_response(status_code: int, payload: dict | None = None):
    response = MagicMock()
    response.status_code = status_code
    response.content = b"{}"
    response.text = ""
    response.json.return_value = payload or {}
    return response


@pytest.mark.django_db
class TestPaddleService:
    def test_create_checkout_uses_plan_price(self, organization, plan):
        _configure_paddle()
        PlanPrice.objects.create(
            plan=plan,
            paddle_price_id="pri_abc",
            interval="month",
            amount=Decimal("49.00"),
            currency="USD",
        )
        service = PaddleBillingService()

        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(
                201,
                {"data": {"checkout": {"url": "https://pay.example/123"}}},
            ),
        ) as mock_request:
            session = service.create_checkout(organization=organization, plan=plan)

        assert session.checkout_url == "https://pay.example/123"
        kwargs = mock_request.call_args.kwargs
        assert kwargs["json"]["items"][0]["price_id"] == "pri_abc"

    def test_test_credentials_calls_paddle_event_types(self):
        _configure_paddle()
        service = PaddleBillingService()
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(200, {"data": []}),
        ) as mock_request:
            ok, detail = service.test_credentials()
        assert ok is True
        assert "sandbox" in detail
        assert mock_request.call_args.args[1].endswith("/event-types")

    def test_push_plan_creates_product_when_no_paddle_id(self, plan):
        _configure_paddle()
        PlanEntitlement.objects.create(
            plan=plan,
            feature_key="ai.usage",
            enabled=True,
            limit=1000,
            period=PlanEntitlement.Period.MONTHLY,
        )
        service = PaddleBillingService()
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(201, {"data": {"id": "pro_123"}}),
        ) as mock_request:
            service.push_plan(plan)
        assert mock_request.call_args.args[0] == "POST"
        assert mock_request.call_args.args[1].endswith("/products")
        payload = mock_request.call_args.kwargs["json"]
        assert payload["custom_data"]["entitlements"] == [
            {
                "feature_key": "ai.usage",
                "limit": 1000,
                "period": PlanEntitlement.Period.MONTHLY,
            },
        ]
        plan.refresh_from_db()
        assert plan.paddle_product_id == "pro_123"

    def test_push_plan_updates_existing_product(self, plan):
        _configure_paddle()
        plan.paddle_product_id = "pro_existing"
        plan.save(update_fields=["paddle_product_id"])

        service = PaddleBillingService()
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(200, {"data": {"id": "pro_existing"}}),
        ) as mock_request:
            service.push_plan(plan)
        assert mock_request.call_args.args[0] == "PATCH"
        assert mock_request.call_args.args[1].endswith("/products/pro_existing")

    def test_cancel_calls_paddle_endpoint(self, organization, plan):
        _configure_paddle()
        sub = Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider_subscription_id="sub_42",
            status=Subscription.Status.ACTIVE,
        )
        service = PaddleBillingService()
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(200, {"data": {"id": "sub_42"}}),
        ) as mock_request:
            service.cancel(sub)
        assert mock_request.call_args.args[1].endswith("/subscriptions/sub_42/cancel")


@pytest.mark.django_db
class TestPaddleAdminPushes:
    def test_plan_admin_save_pushes_to_paddle(self, admin_client):
        _configure_paddle()
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(201, {"data": {"id": "pro_42"}}),
        ) as mock_request:
            response = admin_client.post(
                reverse("admin:billing_plan_add"),
                {
                    "name": "Pro",
                    "code": "pro",
                    "base_price": "29.00",
                    "currency": "USD",
                    "region": "US",
                    "features": "[]",
                    "is_active": "on",
                },
            )
        assert response.status_code in (200, 302)
        assert Plan.objects.filter(code="pro", paddle_product_id="pro_42").exists()
        assert mock_request.called

    def test_subscription_admin_cancel_action_calls_paddle(
        self,
        admin_client,
        organization,
        plan,
    ):
        _configure_paddle()
        sub = Subscription.objects.create(
            organization=organization,
            plan=plan,
            provider_subscription_id="sub_admin",
            status=Subscription.Status.ACTIVE,
        )
        with patch(
            "talk2record.billing.paddle_client.requests.request",
            return_value=_fake_response(
                200,
                {"data": {"id": sub.provider_subscription_id}},
            ),
        ) as mock_request:
            response = admin_client.post(
                reverse("admin:billing_subscription_changelist"),
                {
                    "action": "cancel_now",
                    "_selected_action": [str(sub.pk)],
                    "index": 0,
                },
            )
        assert response.status_code in (200, 302)
        assert any(
            call.args[1].endswith("/subscriptions/sub_admin/cancel")
            for call in mock_request.call_args_list
        )


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
