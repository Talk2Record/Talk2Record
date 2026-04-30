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
