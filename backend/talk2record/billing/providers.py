from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from talk2record.billing.stripe_runtime import get_active_stripe_settings
from talk2record.billing.stripe_runtime import get_stripe_secret_plaintext


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
        stripe_settings = get_active_stripe_settings()
        if stripe_settings is None:
            return None

        cfg = stripe_settings.config if isinstance(stripe_settings.config, dict) else {}
        provider = str(cfg.get("provider", "stripe")).strip().lower()
        if provider not in cls._providers:
            return None

        # Force runtime credential resolution to ensure admin updates are effective.
        secret = get_stripe_secret_plaintext()
        if secret is None:
            return None
        return cls._providers[provider]
