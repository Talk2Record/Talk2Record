from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

from talk2record.billing.providers import BillingProvider
from talk2record.billing.providers import CheckoutSession
from talk2record.billing.providers import ProviderSubscriptionSnapshot

if TYPE_CHECKING:
    pass


class StripeBillingProvider(BillingProvider):
    """Billing provider backed by the Stripe SDK."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def _stripe(self):
        import stripe  # noqa: PLC0415

        stripe.api_key = self._api_key
        return stripe

    def create_checkout(self, *, organization, plan) -> CheckoutSession:
        stripe = self._stripe()

        success_url = getattr(
            settings,
            "BILLING_SUCCESS_URL",
            "https://app.talk2record.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
        )
        cancel_url = getattr(
            settings,
            "BILLING_CANCEL_URL",
            "https://app.talk2record.com/billing/cancel",
        )

        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[
                {
                    "price_data": {
                        "currency": plan.currency.lower(),
                        "product_data": {"name": plan.name},
                        "unit_amount": int(plan.base_price * 100),
                        "recurring": {"interval": "month"},
                    },
                    "quantity": 1,
                },
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(organization.pk),
            metadata={
                "organization_id": str(organization.pk),
                "plan_code": plan.code,
            },
        )

        return CheckoutSession(
            status="created",
            checkout_url=session.url or "",
        )

    def cancel_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        stripe = self._stripe()
        updated = stripe.Subscription.modify(
            subscription.provider_subscription_id,
            cancel_at_period_end=True,
        )
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=updated.id,
            status=updated.status,
        )

    def get_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        stripe = self._stripe()
        sub = stripe.Subscription.retrieve(subscription.provider_subscription_id)
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=sub.id,
            status=sub.status,
        )

    def list_invoices(self, *, subscription) -> list[dict[str, object]]:
        stripe = self._stripe()
        invoices = stripe.Invoice.list(
            subscription=subscription.provider_subscription_id,
            limit=20,
        )
        return [
            {
                "invoice_number": inv.number or inv.id,
                "amount": (inv.amount_paid or 0) / 100,
                "currency": (inv.currency or "usd").upper(),
                "status": inv.status or "unknown",
            }
            for inv in invoices.data
        ]
