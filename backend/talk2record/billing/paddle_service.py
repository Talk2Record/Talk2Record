"""High-level Paddle integration used by the admin and the DRF checkout endpoint.

This module is the single seam between Talk2Record and Paddle:

* ``create_checkout`` mints a transaction the frontend can redirect to.
* ``push_plan`` / ``push_price`` turn admin edits into Paddle product / price
  upserts (two-way sync from our DB → Paddle).
* ``cancel`` / ``pause`` / ``resume`` and ``sync_subscription`` are wired into
  admin actions so staff can manipulate live subscriptions.
* ``test_credentials`` powers the "Test connection" button in the admin and
  the ``admin_test_paddle_connection`` URL.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING
from typing import Any

from django.conf import settings as django_settings

from talk2record.billing.models import Plan
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_client import PaddleClient

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)

PADDLE_DEFAULT_CHECKOUT_URL_ERROR = "transaction_default_checkout_url_not_set"


@dataclass(frozen=True)
class CheckoutSession:
    status: str
    checkout_url: str
    transaction_id: str


@dataclass(frozen=True)
class ChangePlanResult:
    status: str
    plan_code: str


def _amount_to_paddle_minor_units(amount: Decimal | float | int | str) -> str:
    """Convert a decimal amount (e.g. ``49.00``) to Paddle's minor-unit string."""

    value = Decimal(str(amount or 0))
    minor = (value * Decimal(100)).quantize(Decimal("1"))
    return str(int(minor))


def _normalize_trial_period(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    if not raw:
        return None
    interval = str(raw.get("interval") or "").strip()
    frequency = raw.get("frequency")
    if not interval or frequency in (None, "", 0):
        return None
    return {"interval": interval, "frequency": int(frequency)}


def _trial_periods_match(
    local: dict[str, Any] | None,
    remote: dict[str, Any] | None,
) -> bool:
    return _normalize_trial_period(local or {}) == _normalize_trial_period(remote or {})


def format_paddle_checkout_error(exc: PaddleAPIError) -> str:
    message = str(exc)
    if PADDLE_DEFAULT_CHECKOUT_URL_ERROR in message:
        return (
            "Paddle checkout is not configured: set a Default Payment Link in the "
            "Paddle dashboard (Checkout → Checkout settings) and optionally "
            "default_payment_link in Django admin Paddle settings."
        )
    return message


class PaddleBillingService:
    """Operations against Paddle scoped to the platform's single account."""

    def __init__(self, *, client: PaddleClient | None = None) -> None:
        self.client = client or PaddleClient()

    # ------------------------------------------------------------------
    # Health check (admin "Test connection")
    # ------------------------------------------------------------------

    def test_credentials(self) -> tuple[bool, str]:
        if not self.client.is_configured():
            return False, "Paddle API key is not configured."
        try:
            self.client.ping()
        except PaddleAPIError as exc:
            return False, str(exc)
        env = self.client._settings().environment  # noqa: SLF001
        return True, f"Paddle Billing API ({env}) responded successfully to a live ping."

    # ------------------------------------------------------------------
    # Checkout
    # ------------------------------------------------------------------

    def create_checkout(
        self,
        *,
        organization: "Organization",
        plan: Plan,
        success_url: str | None = None,
    ) -> CheckoutSession:
        price = self._resolve_price(plan)
        if price is None or not price.paddle_price_id:
            msg = (
                f"Plan {plan.code!r} has no synced Paddle price. "
                "Save the plan price in the admin first."
            )
            raise PaddleAPIError(msg)

        resolved_success_url = success_url or (
            self.client._settings().default_success_url  # noqa: SLF001
            or getattr(
                django_settings,
                "BILLING_SUCCESS_URL",
                "https://app.talk2record.com/billing/success",
            )
        )
        custom_data: dict[str, str] = {
            "organization_id": str(organization.pk),
            "plan_code": plan.code,
        }
        if resolved_success_url:
            custom_data["success_url"] = resolved_success_url

        payload: dict[str, Any] = {
            "items": [{"price_id": price.paddle_price_id, "quantity": 1}],
            "custom_data": custom_data,
        }
        payment_link = (self.client._settings().default_payment_link or "").strip()  # noqa: SLF001
        if payment_link:
            payload["checkout"] = {"url": payment_link}

        data = self.client.create_transaction(payload)
        body = data.get("data") if isinstance(data, dict) else {}
        if not isinstance(body, dict):
            body = {}
        transaction_id = str(body.get("id") or "")
        checkout = body.get("checkout") or {}
        checkout_url = str(checkout.get("url") or "")
        if not checkout_url and payment_link and transaction_id:
            checkout_url = f"{payment_link.rstrip('/')}?_ptxn={transaction_id}"
        if not checkout_url:
            checkout_url = resolved_success_url
        return CheckoutSession(
            status="created",
            checkout_url=checkout_url,
            transaction_id=transaction_id,
        )

    def change_plan(self, *, subscription: Subscription, new_plan: Plan) -> ChangePlanResult:
        if subscription.plan_id == new_plan.pk:
            raise PaddleAPIError("Organization is already on this plan.")

        price = self._resolve_price(new_plan)
        if price is None or not price.paddle_price_id:
            msg = (
                f"Plan {new_plan.code!r} has no synced Paddle price. "
                "Save the plan price in the admin first."
            )
            raise PaddleAPIError(msg)

        before = {"plan_id": subscription.plan_id, "seats": subscription.seats}
        subscription.plan = new_plan
        subscription.amount = price.amount or new_plan.base_price
        subscription.currency = price.currency or new_plan.currency
        subscription.save(update_fields=["plan", "amount", "currency", "updated_at"])
        self.push_subscription_change(subscription, before=before)
        return ChangePlanResult(status="updated", plan_code=new_plan.code)

    @staticmethod
    def _resolve_price(plan: Plan) -> PlanPrice | None:
        return (
            PlanPrice.objects.filter(plan=plan, active=True)
            .order_by("interval")
            .first()
        )

    # ------------------------------------------------------------------
    # Plan / Price upserts
    # ------------------------------------------------------------------

    def push_plan(self, plan: Plan) -> None:
        payload = {
            "name": plan.name,
            "description": (plan.features and ", ".join(map(str, plan.features))) or "",
            "tax_category": "standard",
            "custom_data": {
                "plan_code": plan.code,
                "region": plan.region or "",
            },
        }
        if plan.paddle_product_id:
            self.client.update_product(plan.paddle_product_id, payload)
            return
        result = self.client.create_product(payload)
        body = result.get("data") if isinstance(result, dict) else {}
        new_id = ""
        if isinstance(body, dict):
            new_id = str(body.get("id") or "")
        if new_id:
            plan.paddle_product_id = new_id
            plan.save(update_fields=["paddle_product_id", "updated_at"])

    def push_price(self, price: PlanPrice) -> None:
        plan = price.plan
        if not plan.paddle_product_id:
            self.push_plan(plan)
        if not plan.paddle_product_id:
            raise PaddleAPIError(
                f"Could not sync plan {plan.code!r} to Paddle — product id is empty.",
            )

        billing_cycle = price.billing_cycle or {
            "interval": price.interval if price.interval != "one_time" else "month",
            "frequency": 1,
        }
        local_trial = _normalize_trial_period(price.trial_period)
        payload: dict[str, Any] = {
            "description": f"{plan.name} ({price.interval})",
            "unit_price": {
                "amount": _amount_to_paddle_minor_units(price.amount or plan.base_price),
                "currency_code": (price.currency or plan.currency).upper(),
            },
            "billing_cycle": billing_cycle,
            "tax_mode": "account_setting",
            "quantity": {"minimum": 1, "maximum": 100},
            "custom_data": {
                "plan_code": plan.code,
                "interval": price.interval,
            },
        }
        if local_trial:
            payload["trial_period"] = local_trial

        if price.paddle_price_id:
            remote_trial = self._remote_trial_period(price.paddle_price_id)
            if not _trial_periods_match(local_trial, remote_trial):
                self.client.update_price(
                    price.paddle_price_id,
                    {"status": "archived"},
                )
                price.paddle_price_id = ""
                price.save(update_fields=["paddle_price_id", "updated_at"])
            else:
                update_payload = {
                    **payload,
                    "status": "active" if price.active else "archived",
                }
                self.client.update_price(price.paddle_price_id, update_payload)
                return

        create_payload = {**payload, "product_id": plan.paddle_product_id}
        result = self.client.create_price(create_payload)
        body = result.get("data") if isinstance(result, dict) else {}
        new_id = ""
        if isinstance(body, dict):
            new_id = str(body.get("id") or "")
        if new_id:
            price.paddle_price_id = new_id
            price.save(update_fields=["paddle_price_id", "updated_at"])

    def _remote_trial_period(self, paddle_price_id: str) -> dict[str, Any] | None:
        try:
            data = self.client.get_price(paddle_price_id)
        except PaddleAPIError:
            return None
        body = data.get("data") if isinstance(data, dict) else {}
        if not isinstance(body, dict):
            return None
        remote = body.get("trial_period") or body.get("trialPeriod")
        return remote if isinstance(remote, dict) else None

    # ------------------------------------------------------------------
    # Subscription mutations
    # ------------------------------------------------------------------

    def push_subscription_change(
        self, sub: Subscription, *, before: dict[str, Any],
    ) -> None:
        """Reconcile admin edits to a Subscription row with Paddle.

        ``before`` is a snapshot captured by the admin before saving so we
        can build a minimal PATCH payload.
        """

        if not sub.provider_subscription_id:
            return
        payload: dict[str, Any] = {}
        if before.get("seats") != sub.seats and sub.seats:
            payload.setdefault("items", []).append(
                {
                    "price_id": self._first_price_id(sub.plan),
                    "quantity": int(sub.seats),
                },
            )
        if before.get("plan_id") != sub.plan_id:
            new_price_id = self._first_price_id(sub.plan)
            if new_price_id:
                payload["items"] = [{"price_id": new_price_id, "quantity": sub.seats or 1}]
                payload["proration_billing_mode"] = "prorated_immediately"
        if not payload:
            return
        try:
            self.client.update_subscription(sub.provider_subscription_id, payload)
        except PaddleAPIError as exc:
            logger.warning(
                "Paddle subscription update failed for %s: %s",
                sub.provider_subscription_id,
                exc,
            )
            raise

    @staticmethod
    def _first_price_id(plan: Plan) -> str:
        price = (
            PlanPrice.objects.filter(plan=plan, active=True)
            .exclude(paddle_price_id="")
            .order_by("interval")
            .first()
        )
        return price.paddle_price_id if price else ""

    def cancel(self, sub: Subscription, *, effective_from: str = "next_billing_period") -> None:
        if not sub.provider_subscription_id:
            return
        self.client.cancel_subscription(
            sub.provider_subscription_id, effective_from=effective_from,
        )

    def pause(self, sub: Subscription) -> None:
        if not sub.provider_subscription_id:
            return
        self.client.pause_subscription(sub.provider_subscription_id)

    def resume(self, sub: Subscription) -> None:
        if not sub.provider_subscription_id:
            return
        self.client.resume_subscription(sub.provider_subscription_id)

    def sync_subscription(self, sub: Subscription) -> None:
        """Pull the live state from Paddle into the local row."""

        if not sub.provider_subscription_id:
            return
        data = self.client.get_subscription(sub.provider_subscription_id)
        body = data.get("data") if isinstance(data, dict) else {}
        if not isinstance(body, dict):
            return

        update_fields: list[str] = []
        new_status = str(body.get("status") or "").lower()
        status_map = {
            "active": Subscription.Status.ACTIVE,
            "trialing": Subscription.Status.TRIALING,
            "paused": Subscription.Status.PAUSED,
            "past_due": Subscription.Status.PAST_DUE,
            "canceled": Subscription.Status.CANCELED,
        }
        if new_status in status_map and sub.status != status_map[new_status]:
            sub.status = status_map[new_status]
            update_fields.append("status")

        customer_id = str(body.get("customer_id") or "")
        if customer_id and customer_id != sub.paddle_customer_id:
            sub.paddle_customer_id = customer_id
            update_fields.append("paddle_customer_id")

        if update_fields:
            update_fields.append("updated_at")
            sub.save(update_fields=update_fields)
