from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret


@dataclass(frozen=True)
class CheckoutSession:
    status: str
    checkout_url: str


@dataclass(frozen=True)
class ProviderSubscriptionSnapshot:
    provider_subscription_id: str
    status: str


class BillingProvider(ABC):
    @abstractmethod
    def create_checkout(self, *, organization, plan) -> CheckoutSession:
        raise NotImplementedError

    @abstractmethod
    def cancel_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        raise NotImplementedError

    @abstractmethod
    def get_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        raise NotImplementedError

    @abstractmethod
    def list_invoices(self, *, subscription) -> list[dict[str, object]]:
        raise NotImplementedError


class MockBillingProvider(BillingProvider):
    def __init__(self, provider_name: str):
        self.provider_name = provider_name

    def create_checkout(self, *, organization, plan) -> CheckoutSession:
        return CheckoutSession(
            status=f"{self.provider_name.title()} checkout prepared for {organization.name}.",
            checkout_url=f"https://billing.example.com/{self.provider_name}/{plan.code}",
        )

    def cancel_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=subscription.provider_subscription_id or f"{self.provider_name}-mock",
            status="canceled",
        )

    def get_subscription(self, *, subscription) -> ProviderSubscriptionSnapshot:
        return ProviderSubscriptionSnapshot(
            provider_subscription_id=subscription.provider_subscription_id or f"{self.provider_name}-mock",
            status=subscription.status,
        )

    def list_invoices(self, *, subscription) -> list[dict[str, object]]:
        return [
            {
                "invoice_number": transaction.invoice_number,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "status": transaction.status,
            }
            for transaction in subscription.transactions.all()
        ]


class BillingProviderRegistry:
    _providers = {
        "stripe": MockBillingProvider("stripe"),
        "paddle": MockBillingProvider("paddle"),
        "paypal": MockBillingProvider("paypal"),
    }

    @classmethod
    def get(cls, provider: str) -> BillingProvider:
        return cls._providers[provider]

    @classmethod
    def get_global_provider(cls) -> BillingProvider | None:
        integration = get_active_integration("stripe")
        if integration is None:
            return None

        provider = str(integration.config.get("provider", "stripe")).strip().lower()
        if provider not in cls._providers:
            return None

        # Force runtime credential resolution to ensure admin updates are effective.
        secret = get_active_integration_secret("stripe")
        if secret is None:
            return None
        return cls._providers[provider]
