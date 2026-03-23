from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.billing.providers import BillingProviderRegistry
from talk2record.billing.tasks import handle_domain_event_for_billing
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.billing.models import StripeSettings
from talk2record.core.vault import SecretVault
from talk2record.notifications.models import Notification


@pytest.mark.django_db
def test_plan_subscription_and_transaction_str(plan, subscription):
    transaction = subscription.transactions.get()

    assert str(plan) == "Growth (USD)"
    assert str(subscription) == f"{subscription.organization.name}: {subscription.plan.name}"
    assert str(transaction) == "inv_1"


@pytest.mark.django_db
def test_mock_billing_provider_methods(plan, subscription):
    provider = BillingProviderRegistry.get("stripe")

    checkout = provider.create_checkout(
        organization=subscription.organization,
        plan=plan,
    )
    canceled = provider.cancel_subscription(subscription=subscription)
    snapshot = provider.get_subscription(subscription=subscription)
    invoices = provider.list_invoices(subscription=subscription)

    assert checkout.checkout_url.endswith("/stripe/growth")
    assert canceled.status == "canceled"
    assert snapshot.status == subscription.status
    assert invoices[0]["invoice_number"] == "inv_1"


@pytest.mark.django_db
def test_billing_admin_pages(admin_client, subscription):
    urls = [
        reverse("admin:billing_plan_changelist"),
        reverse("admin:billing_subscription_changelist"),
        reverse("admin:billing_transaction_changelist"),
        reverse("admin:billing_stripesettings_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_global_stripe_provider_requires_enabled_settings_with_credential():
    assert BillingProviderRegistry.get_global_provider() is None

    s = StripeSettings.get_solo()
    s.enabled = True
    s.config = {"provider": "stripe"}
    s.encrypted_credential = SecretVault.encrypt("stripe-secret")
    s.save(update_fields=["enabled", "config", "encrypted_credential", "updated_at"])

    provider = BillingProviderRegistry.get_global_provider()
    assert provider is not None


@pytest.mark.django_db
def test_handle_domain_event_for_billing_payment_failed_creates_notifications(
    workspace_user, organization
):
    event_payload = {
        "event_id": "billing-test-uuid-001",
        "name": BILLING_PAYMENT_FAILED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "stripe",
        "metadata": {"provider": "stripe"},
    }

    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_PAYMENT,
    ).exists()


@pytest.mark.django_db
def test_handle_domain_event_for_billing_subscription_created_creates_notifications(
    workspace_user, organization
):
    event_payload = {
        "event_id": "billing-test-uuid-002",
        "name": BILLING_SUBSCRIPTION_CREATED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "stripe",
        "metadata": {"provider": "stripe"},
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
        "resource_id": "stripe",
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

    with patch("talk2record.billing.views.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook", kwargs={"provider": "stripe"}),
            data={"type": "payment_failed", "organization_id": subscription.organization_id},
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_PAYMENT_FAILED in published


@pytest.mark.django_db(transaction=True)
def test_billing_webhook_view_emits_subscription_created_event(settings, subscription):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    published: list[str] = []

    with patch("talk2record.billing.views.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook", kwargs={"provider": "stripe"}),
            data={"type": "subscription_created", "organization_id": subscription.organization_id},
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_SUBSCRIPTION_CREATED in published
