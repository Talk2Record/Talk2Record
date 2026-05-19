from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.billing.models import PaddleSettings
from talk2record.billing.tasks import handle_domain_event_for_billing
from talk2record.core.vault import SecretVault
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.notifications.models import Notification


@pytest.mark.django_db
def test_plan_subscription_and_transaction_str(plan, subscription):
    transaction = subscription.transactions.get()

    assert str(plan) == "Growth (USD)"
    assert str(subscription) == f"{subscription.organization.name}: {subscription.plan.name}"
    assert str(transaction) == "inv_1"


@pytest.mark.django_db
def test_billing_admin_pages(admin_client, subscription):
    urls = [
        reverse("admin:billing_plan_changelist"),
        reverse("admin:billing_subscription_changelist"),
        reverse("admin:billing_transaction_changelist"),
        reverse("admin:billing_paddlesettings_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_paddle_settings_singleton_persists_environment_and_secrets():
    settings = PaddleSettings.get_solo()
    settings.environment = PaddleSettings.Environment.PRODUCTION
    settings.encrypted_api_key = SecretVault.encrypt("pdl_live_secret")
    settings.save(
        update_fields=["environment", "encrypted_api_key", "updated_at"],
    )

    from talk2record.billing.paddle_client import PaddleClient

    client = PaddleClient()
    assert client.base_url() == PaddleClient.PRODUCTION_BASE_URL
    assert client.api_key() == "pdl_live_secret"


@pytest.mark.django_db
def test_paddle_settings_environment_toggle_changes_base_url():
    settings = PaddleSettings.get_solo()
    settings.environment = PaddleSettings.Environment.SANDBOX
    settings.encrypted_api_key = SecretVault.encrypt("pdl_sandbox")
    settings.save(
        update_fields=["environment", "encrypted_api_key", "updated_at"],
    )

    from talk2record.billing.paddle_client import PaddleClient

    client = PaddleClient()
    assert client.base_url() == PaddleClient.SANDBOX_BASE_URL

    settings.environment = PaddleSettings.Environment.PRODUCTION
    settings.save(update_fields=["environment", "updated_at"])

    assert client.base_url() == PaddleClient.PRODUCTION_BASE_URL


@pytest.mark.django_db
def test_handle_domain_event_for_billing_payment_failed_creates_notifications(
    workspace_user, organization,
):
    event_payload = {
        "event_id": "billing-test-uuid-001",
        "name": BILLING_PAYMENT_FAILED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {"provider": "paddle"},
    }

    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_PAYMENT,
    ).exists()


@pytest.mark.django_db
def test_handle_domain_event_for_billing_subscription_created_creates_notifications(
    workspace_user, organization,
):
    event_payload = {
        "event_id": "billing-test-uuid-002",
        "name": BILLING_SUBSCRIPTION_CREATED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {"provider": "paddle"},
    }

    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_SUBSCRIPTION,
    ).exists()


@pytest.mark.django_db
def test_handle_domain_event_for_billing_is_idempotent(workspace_user, organization):
    event_payload = {
        "event_id": "billing-test-uuid-003",
        "name": BILLING_PAYMENT_FAILED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {},
    }

    handle_domain_event_for_billing(event_payload)
    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_PAYMENT,
        metadata__event_id="billing-test-uuid-003",
    ).count() == 1


@pytest.mark.django_db(transaction=True)
def test_billing_webhook_view_emits_payment_failed_event(settings, subscription):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    published: list[str] = []

    payload = {
        "event_type": "transaction.payment_failed",
        "data": {
            "id": "txn_failed_1",
            "subscription_id": subscription.provider_subscription_id,
            "currency_code": "USD",
            "details": {"totals": {"grand_total": "4900"}},
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    with patch("talk2record.billing.views.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_PAYMENT_FAILED in published


@pytest.mark.django_db(transaction=True)
def test_billing_webhook_view_emits_subscription_created_event(settings, subscription):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    published: list[str] = []

    payload = {
        "event_type": "subscription.created",
        "data": {
            "id": "sub_xyz",
            "status": "active",
            "items": [],
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    with patch("talk2record.billing.views.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_SUBSCRIPTION_CREATED in published


@pytest.mark.django_db
def test_plans_catalog_is_public(client):
    from talk2record.billing.models import Plan
    from talk2record.seed.constants import PLAN_DEFINITIONS

    for definition in PLAN_DEFINITIONS:
        Plan.objects.update_or_create(
            code=definition["code"],
            defaults={
                "name": definition["name"],
                "base_price": definition["base_price"],
                "currency": definition["currency"],
                "region": definition.get("region", ""),
                "features": list(definition.get("features", [])),
                "is_active": True,
            },
        )

    response = client.get(reverse("api:billing-plans"))
    assert response.status_code == HTTPStatus.OK
    codes = {row["code"] for row in response.json()}
    assert "starter" in codes
    assert "growth" in codes
    assert "scale" in codes
    growth = next(row for row in response.json() if row["code"] == "growth")
    assert growth["monthly_amount"] is not None
    assert "entitlements" in growth


@pytest.mark.django_db
def test_change_plan_updates_subscription(workspace_user, subscription, plan):
    from decimal import Decimal

    from talk2record.billing.models import Plan
    from talk2record.billing.models import PlanPrice

    starter, _ = Plan.objects.get_or_create(
        code="starter",
        defaults={
            "name": "Starter",
            "base_price": Decimal("19.00"),
            "currency": "USD",
            "region": "US",
            "features": [],
        },
    )
    PlanPrice.objects.update_or_create(
        plan=starter,
        interval="month",
        currency="USD",
        defaults={"amount": Decimal("19.00"), "active": True, "paddle_price_id": "pri_starter"},
    )
    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={"amount": Decimal("49.00"), "active": True, "paddle_price_id": "pri_growth"},
    )

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True
        mock_service.change_plan.return_value = type(
            "R",
            (),
            {"status": "updated", "plan_code": "starter"},
        )()

        response = client.post(
            reverse("api:billing-change-plan"),
            {"plan": "starter", "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["status"] == "updated"
    mock_service.change_plan.assert_called_once()


@pytest.mark.django_db
def test_change_plan_same_plan_returns_400(workspace_user, subscription):
    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True

        response = client.post(
            reverse("api:billing-change-plan"),
            {"plan": subscription.plan.code, "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_change_plan_without_subscription_returns_checkout(workspace_user, organization, plan):
    from talk2record.billing.models import PlanPrice

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={"amount": plan.base_price, "active": True, "paddle_price_id": "pri_growth"},
    )

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True
        mock_service.create_checkout.return_value = type(
            "S",
            (),
            {
                "status": "created",
                "checkout_url": "http://localhost:3000/checkout?_ptxn=txn_test",
                "transaction_id": "txn_test",
            },
        )()

        response = client.post(
            reverse("api:billing-change-plan"),
            {"plan": plan.code, "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["status"] == "checkout_required"
    assert body["checkoutUrl"].startswith("http://")
    assert body["transactionId"] == "txn_test"


@pytest.mark.django_db
def test_create_checkout_does_not_send_success_url_as_checkout_url(organization, plan):
    from talk2record.billing.models import PlanPrice
    from talk2record.billing.paddle_service import PaddleBillingService

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={"amount": plan.base_price, "active": True, "paddle_price_id": "pri_growth"},
    )

    service = PaddleBillingService()
    captured: dict = {}

    def fake_create_transaction(payload):
        captured["payload"] = payload
        return {
            "data": {
                "id": "txn_abc",
                "checkout": {"url": "http://localhost:3000/checkout?_ptxn=txn_abc"},
            },
        }

    service.client.create_transaction = fake_create_transaction  # type: ignore[method-assign]
    service.client._settings = lambda: type(  # type: ignore[method-assign]  # noqa: SLF001
        "S",
        (),
        {
            "default_success_url": "",
            "default_payment_link": "http://localhost:3000/checkout",
        },
    )()

    session = service.create_checkout(
        organization=organization,
        plan=plan,
        success_url="http://localhost:3000/onboarding?checkout=success",
    )

    payload = captured["payload"]
    assert payload["checkout"]["url"] == "http://localhost:3000/checkout"
    assert payload["custom_data"]["success_url"] == "http://localhost:3000/onboarding?checkout=success"
    assert session.transaction_id == "txn_abc"
    assert session.checkout_url.endswith("?_ptxn=txn_abc")


@pytest.mark.django_db
def test_paddle_config_requires_client_side_token(workspace_user):
    settings = PaddleSettings.get_solo()
    settings.client_side_token = ""
    settings.save(update_fields=["client_side_token", "updated_at"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    response = client.get(reverse("api:billing-paddle-config"))
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_paddle_config_returns_token(workspace_user):
    settings = PaddleSettings.get_solo()
    settings.client_side_token = "test_example_token"
    settings.environment = PaddleSettings.Environment.SANDBOX
    settings.save(update_fields=["client_side_token", "environment", "updated_at"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    response = client.get(reverse("api:billing-paddle-config"))
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["clientSideToken"] == "test_example_token"
    assert body["environment"] == "sandbox"


@pytest.mark.django_db
def test_plans_catalog_includes_trial_period(client):
    from talk2record.billing.models import Plan
    from talk2record.billing.models import PlanPrice
    from talk2record.seed.constants import PLAN_DEFINITIONS

    for definition in PLAN_DEFINITIONS:
        plan, _ = Plan.objects.update_or_create(
            code=definition["code"],
            defaults={
                "name": definition["name"],
                "base_price": definition["base_price"],
                "currency": definition["currency"],
                "region": definition.get("region", ""),
                "features": list(definition.get("features", [])),
                "is_active": True,
            },
        )
        for price in definition.get("prices", ()):
            PlanPrice.objects.update_or_create(
                plan=plan,
                interval=price["interval"],
                currency=price["currency"],
                defaults={
                    "amount": price["amount"],
                    "billing_cycle": dict(price.get("billing_cycle") or {}),
                    "trial_period": dict(price.get("trial_period") or {}),
                    "active": True,
                },
            )

    response = client.get(reverse("api:billing-plans"))
    assert response.status_code == HTTPStatus.OK
    starter = next(row for row in response.json() if row["code"] == "starter")
    monthly = next(price for price in starter["prices"] if price["interval"] == "month")
    assert monthly["trialPeriod"] == {"interval": "day", "frequency": 14}
    scale = next(row for row in response.json() if row["code"] == "scale")
    scale_monthly = next(price for price in scale["prices"] if price["interval"] == "month")
    assert scale_monthly["trialPeriod"] is None
