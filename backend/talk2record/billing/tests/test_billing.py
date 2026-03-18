from http import HTTPStatus

import pytest
from django.urls import reverse

from talk2record.billing.providers import BillingProviderRegistry


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
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK
