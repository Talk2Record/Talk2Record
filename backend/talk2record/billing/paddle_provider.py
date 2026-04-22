"""Paddle Billing API v2 provider adapter.

Only the pieces needed by the platform are implemented (checkout creation,
fetching a subscription, cancelling, and listing invoices).

Paddle docs: https://developer.paddle.com/api-reference/overview
"""

from __future__ import annotations

from typing import Any

import requests
from django.conf import settings

from talk2record.billing.providers import (
    BillingProvider,
    CheckoutSession,
    ProviderSubscriptionSnapshot,
)


class PaddleAPIError(RuntimeError):
    """Raised when Paddle returns a non-2xx response."""


def _base_url(environment: str) -> str:
    env = (environment or "sandbox").strip().lower()
    if env.startswith("prod"):
        return "https://api.paddle.com"
    return "https://sandbox-api.paddle.com"


class PaddleBillingProvider(BillingProvider):
    def __init__(
        self,
        *,
        api_key: str,
        environment: str = "sandbox",
        default_price_id: str = "",
    ) -> None:
        self._api_key = api_key
        self._environment = environment
        self._base = _base_url(environment)
        self._default_price_id = default_price_id

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Paddle-Version": "1",
        }

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
        url = f"{self._base}{path}"
        response = requests.request(
            method,
            url,
            headers=self._headers(),
            json=payload,
            timeout=15,
        )
        if response.status_code >= 400:
            msg = f"Paddle {method} {path} failed: {response.status_code} {response.text}"
            raise PaddleAPIError(msg)
        data = response.json() if response.content else {}
        return data if isinstance(data, dict) else {}

    def _resolve_price_id(self, *, plan) -> str:
        from talk2record.billing.models import PlanProviderPrice

        pricing = (
            PlanProviderPrice.objects.filter(
                plan=plan,
                provider="paddle",
                active=True,
            )
            .order_by("interval")
            .first()
        )
        if pricing is not None and pricing.provider_price_id:
            return pricing.provider_price_id
        return self._default_price_id

    def create_checkout(self, *, organization, plan) -> CheckoutSession:
        price_id = self._resolve_price_id(plan=plan)
        if not price_id:
            msg = "Missing Paddle price_id for plan {!r}.".format(plan.code)
            raise PaddleAPIError(msg)

        success_url = getattr(
            settings,
            "BILLING_SUCCESS_URL",
            "https://app.talk2record.com/billing/success",
        )
        payload: dict[str, Any] = {
            "items": [{"price_id": price_id, "quantity": 1}],
            "custom_data": {
                "organization_id": str(organization.pk),
                "plan_code": plan.code,
            },
            "checkout": {"url": success_url},
        }
        data = self._request("POST", "/transactions", payload=payload)
        transaction = data.get("data") or {}
        checkout = transaction.get("checkout") or {}
        checkout_url = str(checkout.get("url") or success_url)
        return CheckoutSession(status="created", checkout_url=checkout_url)

    def cancel_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        sub_id = subscription.provider_subscription_id
        if not sub_id:
            msg = "Subscription has no Paddle provider id."
            raise PaddleAPIError(msg)
        data = self._request(
            "POST",
            f"/subscriptions/{sub_id}/cancel",
            payload={"effective_from": "next_billing_period"},
        )
        payload = data.get("data") or {}
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=str(payload.get("id") or sub_id),
            status=str(payload.get("status") or "canceled"),
        )

    def get_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        sub_id = subscription.provider_subscription_id
        data = self._request("GET", f"/subscriptions/{sub_id}")
        payload = data.get("data") or {}
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=str(payload.get("id") or sub_id),
            status=str(payload.get("status") or subscription.status),
        )

    def list_invoices(self, *, subscription) -> list[dict[str, object]]:
        sub_id = subscription.provider_subscription_id
        data = self._request(
            "GET",
            f"/transactions?subscription_id={sub_id}&per_page=20",
        )
        items = data.get("data") or []
        invoices: list[dict[str, object]] = []
        if isinstance(items, list):
            for item in items:
                if not isinstance(item, dict):
                    continue
                details = item.get("details") or {}
                totals = details.get("totals") or {}
                invoices.append(
                    {
                        "invoice_number": str(item.get("invoice_number") or item.get("id") or ""),
                        "amount": str(totals.get("grand_total") or "0"),
                        "currency": str(item.get("currency_code") or "USD"),
                        "status": str(item.get("status") or "unknown"),
                    },
                )
        return invoices
