"""Thin REST client for the Paddle Billing API.

A single :class:`PaddleClient` instance reads its credentials and base URL
from :class:`~talk2record.billing.models.PaddleSettings` (the singleton row
in the admin) so toggling environment from Sandbox to Production immediately
re-points subsequent calls at the live API.

Only the endpoints used by the platform (products, prices, subscriptions,
transactions, notification settings) are wrapped — this is not a complete
SDK.
"""

from __future__ import annotations

import logging
from typing import Any
from typing import Iterable

import requests
from django.core import signing

from talk2record.billing.models import PaddleSettings
from talk2record.core.vault import SecretVault

logger = logging.getLogger(__name__)


PADDLE_API_VERSION = "1"
DEFAULT_TIMEOUT = 15


class PaddleAPIError(RuntimeError):
    """Raised when Paddle returns a non-2xx response or a transport error."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class PaddleClient:
    """Minimal REST helper bound to the current ``PaddleSettings`` singleton.

    The client re-reads the singleton on every call (cheap: one cached row in
    ``pk=1``) so admins toggling the environment field, rotating keys, or
    disabling Paddle are picked up without restarting workers.
    """

    SANDBOX_BASE_URL = "https://sandbox-api.paddle.com"
    PRODUCTION_BASE_URL = "https://api.paddle.com"

    def __init__(self, *, settings: PaddleSettings | None = None) -> None:
        self._settings_override = settings

    def _settings(self) -> PaddleSettings:
        if self._settings_override is not None:
            return self._settings_override
        return PaddleSettings.get_solo()

    def base_url(self) -> str:
        env = (self._settings().environment or "sandbox").strip().lower()
        if env == PaddleSettings.Environment.PRODUCTION:
            return self.PRODUCTION_BASE_URL
        return self.SANDBOX_BASE_URL

    def api_key(self) -> str:
        raw = (self._settings().encrypted_api_key or "").strip()
        if not raw:
            return ""
        try:
            return SecretVault.decrypt(raw)
        except signing.BadSignature:
            logger.warning("Paddle API key failed to decrypt; storage may be corrupt.")
            return ""

    def webhook_secret(self) -> str:
        raw = (self._settings().encrypted_webhook_secret or "").strip()
        if not raw:
            return ""
        try:
            return SecretVault.decrypt(raw)
        except signing.BadSignature:
            return ""

    def is_configured(self) -> bool:
        return bool(self.api_key())

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key()}",
            "Content-Type": "application/json",
            "Paddle-Version": PADDLE_API_VERSION,
        }

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if not self.is_configured():
            raise PaddleAPIError("Paddle credentials are not configured.")
        url = f"{self.base_url()}{path}"
        try:
            response = requests.request(
                method,
                url,
                headers=self._headers(),
                json=json,
                params=params,
                timeout=timeout,
            )
        except requests.RequestException as exc:
            raise PaddleAPIError(
                f"Paddle {method} {path} transport error: {exc}",
            ) from exc

        if response.status_code >= 400:
            raise PaddleAPIError(
                f"Paddle {method} {path} failed: "
                f"{response.status_code} {response.text[:500]}",
                status_code=response.status_code,
            )
        if not response.content:
            return {}
        try:
            data = response.json()
        except ValueError as exc:
            raise PaddleAPIError(
                f"Paddle {method} {path} returned invalid JSON.",
            ) from exc
        return data if isinstance(data, dict) else {"data": data}

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def create_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/products", json=payload)

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/products/{product_id}", json=payload)

    def get_product(self, product_id: str) -> dict[str, Any]:
        return self.request("GET", f"/products/{product_id}")

    # ------------------------------------------------------------------
    # Prices
    # ------------------------------------------------------------------

    def create_price(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/prices", json=payload)

    def update_price(self, price_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("PATCH", f"/prices/{price_id}", json=payload)

    def get_price(self, price_id: str) -> dict[str, Any]:
        return self.request("GET", f"/prices/{price_id}")

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def get_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self.request("GET", f"/subscriptions/{subscription_id}")

    def update_subscription(
        self, subscription_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.request("PATCH", f"/subscriptions/{subscription_id}", json=payload)

    def cancel_subscription(
        self,
        subscription_id: str,
        *,
        effective_from: str = "next_billing_period",
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/subscriptions/{subscription_id}/cancel",
            json={"effective_from": effective_from},
        )

    def pause_subscription(
        self,
        subscription_id: str,
        *,
        effective_from: str = "next_billing_period",
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/subscriptions/{subscription_id}/pause",
            json={"effective_from": effective_from},
        )

    def resume_subscription(
        self,
        subscription_id: str,
        *,
        effective_from: str = "immediately",
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/subscriptions/{subscription_id}/resume",
            json={"effective_from": effective_from},
        )

    def activate_trialing_subscription(self, subscription_id: str) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/subscriptions/{subscription_id}/activate",
            json={},
        )

    def get_update_payment_method_transaction(
        self, subscription_id: str,
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/subscriptions/{subscription_id}/update-payment-method-transaction",
        )

    def list_subscriptions(
        self,
        *,
        status: Iterable[str] | None = None,
        per_page: int = 50,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"per_page": per_page}
        if status:
            params["status"] = ",".join(status)
        return self.request("GET", "/subscriptions", params=params)

    # ------------------------------------------------------------------
    # Transactions / checkout
    # ------------------------------------------------------------------

    def create_transaction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/transactions", json=payload)

    def list_transactions(
        self,
        *,
        subscription_id: str | None = None,
        per_page: int = 20,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"per_page": per_page}
        if subscription_id:
            params["subscription_id"] = subscription_id
        return self.request("GET", "/transactions", params=params)

    def get_transaction_invoice(self, transaction_id: str) -> dict[str, Any]:
        return self.request("GET", f"/transactions/{transaction_id}/invoice")

    # ------------------------------------------------------------------
    # Notification settings (webhooks)
    # ------------------------------------------------------------------

    def list_notification_settings(self) -> dict[str, Any]:
        return self.request("GET", "/notification-settings")

    def create_notification_setting(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", "/notification-settings", json=payload)

    def update_notification_setting(
        self, setting_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self.request(
            "PATCH",
            f"/notification-settings/{setting_id}",
            json=payload,
        )

    def ensure_webhook_endpoint(
        self,
        *,
        destination: str,
        description: str = "Talk2Record webhook",
        subscribed_events: Iterable[str] | None = None,
    ) -> dict[str, Any]:
        events = list(
            subscribed_events
            or (
                "subscription.created",
                "subscription.activated",
                "subscription.updated",
                "subscription.canceled",
                "subscription.past_due",
                "subscription.paused",
                "subscription.resumed",
                "transaction.completed",
                "transaction.payment_failed",
            ),
        )
        settings = self._settings()
        payload = {
            "description": description,
            "destination": destination,
            "type": "url",
            "active": True,
            "subscribed_events": [{"name": event} for event in events],
        }
        if settings.paddle_notification_setting_id:
            return self.update_notification_setting(
                settings.paddle_notification_setting_id, payload,
            )
        result = self.create_notification_setting(payload)
        new_id = ""
        data = result.get("data") if isinstance(result, dict) else None
        if isinstance(data, dict):
            new_id = str(data.get("id") or "")
        if new_id:
            settings.paddle_notification_setting_id = new_id
            settings.save(
                update_fields=[
                    "paddle_notification_setting_id",
                    "updated_at",
                ],
            )
        return result

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def ping(self) -> dict[str, Any]:
        """Cheap authenticated GET used by the admin "Test connection" button."""

        return self.request("GET", "/event-types")
