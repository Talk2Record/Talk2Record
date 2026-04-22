from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from dataclasses import dataclass

from talk2record.billing.runtime import (
    get_billing_provider_config,
    get_provider_api_key,
    get_provider_config_blob,
)
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
    _mock_providers: dict[str, BillingProvider] = {
        "paypal": MockBillingProvider("paypal"),
    }

    @classmethod
    def get(cls, provider: str) -> BillingProvider:
        """Return a live provider adapter if credentials exist, else a mock."""

        api_key = get_provider_api_key(provider)
        if provider == "stripe" and api_key:
            from talk2record.billing.stripe_provider import StripeBillingProvider  # noqa: PLC0415

            return StripeBillingProvider(api_key=api_key)

        if provider == "paddle" and api_key:
            from talk2record.billing.paddle_provider import PaddleBillingProvider  # noqa: PLC0415

            config = get_billing_provider_config("paddle")
            blob = get_provider_config_blob("paddle")
            return PaddleBillingProvider(
                api_key=api_key,
                environment=(config.environment if config else "sandbox"),
                default_price_id=str(blob.get("default_price_id", "")),
            )

        return cls._mock_providers.get(provider, MockBillingProvider(provider))

    @classmethod
    def get_global_provider(cls) -> BillingProvider | None:
        """Return the platform's primary billing provider, or ``None``.

        Preference order:
        1. The first enabled ``BillingProviderConfig`` row.
        2. Legacy Stripe singleton (``StripeSettings``).
        """

        from talk2record.billing.models import BillingProviderConfig

        first_enabled = (
            BillingProviderConfig.objects.filter(enabled=True)
            .order_by("created_at")
            .first()
        )
        if first_enabled is not None:
            return cls.get(first_enabled.provider)

        stripe_settings = get_active_stripe_settings()
        if stripe_settings is None:
            return None

        cfg = stripe_settings.config if isinstance(stripe_settings.config, dict) else {}
        provider = str(cfg.get("provider", "stripe")).strip().lower()

        secret = get_stripe_secret_plaintext()
        if secret is None:
            return None

        if provider == "stripe":
            from talk2record.billing.stripe_provider import StripeBillingProvider  # noqa: PLC0415

            return StripeBillingProvider(api_key=secret)
        return cls._mock_providers.get(provider)
