"""Paddle webhook ingestion pipeline.

Lives **outside** ``billing/views.py`` so the same dispatch logic can be
reached from three call sites without duplication:

1. ``BillingWebhookView`` (synchronous HTTP entry point).
2. ``billing.tasks.process_paddle_webhook`` (async Celery worker; optional
   path for when synchronous dispatch is too slow).
3. ``PaddleWebhookEventAdmin.replay_events`` (support recovery tooling).

Pipeline (idempotency + replay protection + reset-race guard):

    parse event_id / event_type / org_id / sub_id from payload
        ↓
    INSERT PaddleWebhookEvent(paddle_event_id=event_id)
        ↓ IntegrityError ⇒ duplicate → return early (already applied)
    snapshot org.billing_state_version_at_dispatch
        ↓
    dispatch_event(event_type, event_data, org_id)   ← inside @transaction.atomic
        ↓
    on commit: refresh org; if billing_state_version changed during dispatch
       ⇒ status = SKIPPED, audit row, do **not** retry
        ↓
    mark event status = ACCEPTED | SKIPPED | FAILED, stamp processed_at

This module is intentionally side-effect-light at import time so unit
tests can import it without booting Celery.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any

from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from talk2record.audit.services import AuditService
from talk2record.billing.models import PaddleWebhookEvent
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.events import DomainEvent
from talk2record.events.bus import EventBus
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pure helpers (shared with billing.views via re-export below)
# ---------------------------------------------------------------------------


def _parse_paddle_datetime(value: object) -> datetime.datetime | None:
    """Best-effort ISO-8601 parse of a Paddle webhook timestamp."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_period_end(event_data: dict) -> datetime.datetime | None:
    """Resolve ``current_period_end`` from a Paddle subscription payload.

    Prefers ``current_billing_period.ends_at`` (canonical), falls back to
    ``next_billed_at`` (covers trialing → first paid charge).
    """
    period = event_data.get("current_billing_period")
    ends_at = period.get("ends_at") if isinstance(period, dict) else None
    return _parse_paddle_datetime(ends_at or event_data.get("next_billed_at"))


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SignatureCheck:
    ok: bool
    reason: str = ""


def verify_paddle_signature(
    raw_body: bytes,
    signature_header: str,
    secret: str,
) -> SignatureCheck:
    """Verify a Paddle webhook signature (``Paddle-Signature: ts=...;h1=...``).

    Returns ``SignatureCheck(ok=True)`` when verification passes (or when no
    secret is configured — local-dev convenience). Returns ``ok=False`` with
    a machine-readable ``reason`` otherwise.
    """
    if not secret:
        # No webhook secret configured — caller may opt to accept anyway.
        return SignatureCheck(ok=True, reason="no_secret_configured")

    parts = dict(
        item.split("=", 1) for item in signature_header.split(";") if "=" in item
    )
    ts = parts.get("ts", "")
    h1 = parts.get("h1", "")
    if not ts or not h1:
        return SignatureCheck(ok=False, reason="missing_signature_header")

    signed_payload = f"{ts}:{raw_body.decode('utf-8')}".encode()
    expected = hmac.new(
        secret.encode("utf-8"),
        signed_payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, h1):
        return SignatureCheck(ok=False, reason="invalid_signature")
    return SignatureCheck(ok=True)


# ---------------------------------------------------------------------------
# Event metadata extraction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EventMetadata:
    event_id: str
    event_type: str
    event_data: dict
    org_id: str | None
    subscription_id: str


def extract_event_metadata(payload: dict) -> EventMetadata:
    """Parse the identifying bits from a Paddle webhook payload.

    Paddle places the unique delivery id in ``payload.event_id`` (newer API)
    and historically also ``payload.notification_id`` — we prefer event_id
    but accept either, so retries from old infra are still deduped.
    """
    event_type = str(payload.get("event_type", "")).strip()
    event_id = str(
        payload.get("event_id") or payload.get("notification_id") or "",
    ).strip()

    event_data = payload.get("data") or {}
    if not isinstance(event_data, dict):
        event_data = {}

    org_id: str | None = None
    custom_data = event_data.get("custom_data")
    if isinstance(custom_data, dict):
        raw_org = custom_data.get("organization_id")
        if raw_org:
            org_id = str(raw_org)

    sub_id = str(
        event_data.get("subscription_id")
        or (event_data.get("id") if event_type.startswith("subscription.") else "")
        or "",
    )
    return EventMetadata(
        event_id=event_id,
        event_type=event_type,
        event_data=event_data,
        org_id=org_id,
        subscription_id=sub_id,
    )


# ---------------------------------------------------------------------------
# Dispatch (mutation) — the only place we write to Subscription / Transaction
# ---------------------------------------------------------------------------


_CANCEL_TERMINAL_STATUSES = {Subscription.Status.CANCELED}


def _resolve_organization_pk(
    org_id: str | None,
    *,
    customer_id: str,
    provider_subscription_id: str,
) -> int | None:
    """Map a Paddle ``custom_data.organization_id`` to a real ``Organization`` pk.

    Paddle may replay events long after a local DB reset (or from another
    environment) — in those cases ``custom_data`` still carries a stale id
    like ``3`` that no longer exists. We must never 500 on that; we try a
    few fallbacks, then give up so the webhook pipeline can ACK with 202.
    """
    if org_id:
        try:
            pk = int(org_id)
        except (TypeError, ValueError):
            pk = None
        if pk is not None and Organization.objects.filter(pk=pk).exists():
            return pk

    if provider_subscription_id:
        existing_org = (
            Subscription.objects.filter(
                provider_subscription_id=provider_subscription_id,
            )
            .values_list("organization_id", flat=True)
            .first()
        )
        if existing_org is not None:
            return existing_org

    if customer_id:
        existing_org = (
            Subscription.objects.filter(paddle_customer_id=customer_id)
            .values_list("organization_id", flat=True)
            .first()
        )
        if existing_org is not None:
            return existing_org

    return None


def _upsert_paddle_subscription(
    event_type: str,
    event_data: dict,
    org_id: str | None,
) -> int | None:
    sub_id = str(event_data.get("id") or "")
    if not sub_id:
        return None

    customer_id = str(event_data.get("customer_id") or "")
    resolved_org_id = _resolve_organization_pk(
        org_id,
        customer_id=customer_id,
        provider_subscription_id=sub_id,
    )
    if resolved_org_id is None:
        logger.warning(
            "Webhook %s skipped: no organization for org_id=%s sub_id=%s customer_id=%s",
            event_type,
            org_id,
            sub_id,
            customer_id,
        )
        return None

    # Out-of-order guard: once a sub is locally CANCELED, a stale
    # ``subscription.updated`` carrying status=active must NOT reactivate it.
    # Only the explicit reactivation events are allowed past this gate.
    reactivation_events = {"subscription.activated", "subscription.resumed"}
    if event_type not in reactivation_events:
        local = (
            Subscription.objects.filter(
                provider_subscription_id=sub_id,
                status__in=_CANCEL_TERMINAL_STATUSES,
            )
            .only("id")
            .first()
        )
        if local is not None:
            logger.info(
                "Webhook %s ignored: subscription %s is locally canceled",
                event_type,
                sub_id,
            )
            return None

    plan: Plan | None = None
    matched_price: PlanPrice | None = None
    items = event_data.get("items") or []
    if isinstance(items, list):
        for item in items:
            price = (item or {}).get("price") or {}
            price_id = price.get("id")
            if not price_id:
                continue
            price_row = (
                PlanPrice.objects.filter(paddle_price_id=price_id)
                .select_related("plan")
                .first()
            )
            if price_row is not None:
                plan = price_row.plan
                matched_price = price_row
                break

    custom_data = event_data.get("custom_data") or {}
    if plan is None and isinstance(custom_data, dict):
        plan_code = str(custom_data.get("plan_code") or "")
        if plan_code:
            plan = Plan.objects.filter(code=plan_code).first()

    if plan is None:
        plan = Plan.objects.first()
    if plan is None:
        return None

    # Fall back to the plan's monthly price when the webhook didn't carry
    # a price we recognise — financial fields still come from Paddle, this
    # just ensures dashboards see a non-NULL billing_interval.
    if matched_price is None:
        interval_hint = ""
        if isinstance(custom_data, dict):
            interval_hint = str(custom_data.get("interval") or "")
        matched_price = (
            PlanPrice.objects.filter(
                plan=plan,
                active=True,
                interval=interval_hint or PlanPrice.Interval.MONTH,
            ).first()
            or PlanPrice.objects.filter(plan=plan, active=True).first()
        )

    defaults: dict[str, object] = {
        "organization_id": resolved_org_id,
        "plan": plan,
        "paddle_customer_id": customer_id,
        "status": event_data.get("status") or Subscription.Status.ACTIVE,
    }
    if matched_price is not None:
        defaults["price"] = matched_price
        defaults["billing_interval"] = matched_price.interval
        if matched_price.amount:
            defaults["amount"] = matched_price.amount
        if matched_price.currency:
            defaults["currency"] = matched_price.currency

    period_end = _extract_period_end(event_data)
    if period_end is not None:
        defaults["current_period_end"] = period_end

    Subscription.objects.update_or_create(
        provider_subscription_id=sub_id,
        defaults=defaults,
    )
    return resolved_org_id


def _record_paddle_transaction(event_data: dict, *, paid: bool) -> None:
    sub_id = str(event_data.get("subscription_id") or "")
    subscription = (
        Subscription.objects.filter(provider_subscription_id=sub_id).first()
        if sub_id
        else None
    )
    if subscription is None:
        return

    details = event_data.get("details") or {}
    totals = details.get("totals") if isinstance(details, dict) else {}
    amount_raw = str((totals or {}).get("grand_total") or "0")
    try:
        amount = float(amount_raw) / 100
    except ValueError:
        amount = 0.0
    currency = str(event_data.get("currency_code") or "USD").upper()
    invoice_id = str(event_data.get("id") or "")
    issued_at = (
        _parse_paddle_datetime(
            event_data.get("billed_at") or event_data.get("created_at"),
        )
        or timezone.now()
    )

    Transaction.objects.update_or_create(
        provider_transaction_id=invoice_id,
        defaults={
            "subscription": subscription,
            "amount": amount,
            "currency": currency,
            "status": (Transaction.Status.PAID if paid else Transaction.Status.FAILED),
            "invoice_number": str(
                event_data.get("invoice_number") or invoice_id,
            ),
            "issued_at": issued_at,
            "paid_at": timezone.now() if paid else None,
            "raw_payload": event_data,
        },
    )


def dispatch_event(
    event_type: str,
    event_data: dict,
    org_id: str | None,
) -> None:
    """Apply the local mutations for a Paddle event.

    Caller is responsible for wrapping this in a transaction + the version
    guard (see ``process_event``).
    """
    base_meta: dict[str, Any] = {
        "provider": "paddle",
        "paddle_event_type": event_type,
    }

    if event_type in {"subscription.created", "subscription.activated"}:
        resolved_org_id = _upsert_paddle_subscription(event_type, event_data, org_id)
        sub_id = str(event_data.get("id") or "")
        if resolved_org_id is None:
            return
        EventBus.publish(
            DomainEvent(
                name=BILLING_SUBSCRIPTION_CREATED,
                organization_id=resolved_org_id,
                user_id=None,
                resource_type="subscription",
                resource_id=sub_id,
                metadata={**base_meta, "provider_subscription_id": sub_id},
            ),
        )
    elif event_type in {"subscription.updated", "subscription.resumed"}:
        _upsert_paddle_subscription(event_type, event_data, org_id)
    elif event_type in {
        "subscription.canceled",
        "subscription.past_due",
        "subscription.paused",
    }:
        sub_id = str(event_data.get("id") or "")
        new_status = {
            "subscription.canceled": Subscription.Status.CANCELED,
            "subscription.past_due": Subscription.Status.PAST_DUE,
            "subscription.paused": Subscription.Status.PAUSED,
        }[event_type]
        update_fields: dict[str, object] = {"status": new_status}
        if event_type == "subscription.canceled":
            canceled_at = (
                _parse_paddle_datetime(
                    event_data.get("canceled_at"),
                )
                or timezone.now()
            )
            update_fields["canceled_at"] = canceled_at
        Subscription.objects.filter(provider_subscription_id=sub_id).update(
            **update_fields,
        )
        if event_type == "subscription.past_due":
            EventBus.publish(
                DomainEvent(
                    name=BILLING_PAYMENT_FAILED,
                    organization_id=org_id,
                    user_id=None,
                    resource_type="subscription",
                    resource_id=sub_id,
                    metadata=base_meta,
                ),
            )
    elif event_type == "transaction.completed":
        _record_paddle_transaction(event_data, paid=True)
    elif event_type == "transaction.payment_failed":
        _record_paddle_transaction(event_data, paid=False)
        EventBus.publish(
            DomainEvent(
                name=BILLING_PAYMENT_FAILED,
                organization_id=org_id,
                user_id=None,
                resource_type="transaction",
                resource_id=str(event_data.get("id") or ""),
                metadata=base_meta,
            ),
        )


# ---------------------------------------------------------------------------
# Full pipeline — idempotency + version guard
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PipelineResult:
    """What the pipeline did with a payload — drives the HTTP response."""

    event: PaddleWebhookEvent | None
    status: str  # "accepted" | "duplicate" | "skipped" | "failed" | "ignored"
    detail: str = ""


def _resolve_org_version(org_id: str | None) -> tuple[Organization | None, int | None]:
    """Look up the org and snapshot its current billing_state_version."""
    if not org_id:
        return None, None
    try:
        org = Organization.objects.only("id", "billing_state_version").get(pk=org_id)
    except (Organization.DoesNotExist, ValueError, TypeError):
        return None, None
    return org, org.billing_state_version


def _create_event_row(
    metadata: EventMetadata,
    payload: dict,
    signature_header: str,
    snapshot_version: int | None,
) -> tuple[PaddleWebhookEvent | None, bool]:
    """Insert a ``PaddleWebhookEvent``; on duplicate paddle_event_id, return ``(existing, True)``.

    Returns ``(row, is_duplicate)``. The unique constraint on
    ``paddle_event_id`` is the natural idempotency key.

    The insert is wrapped in a nested ``atomic()`` so that catching the
    ``IntegrityError`` doesn't poison an outer request-level transaction
    (e.g. when ``ATOMIC_REQUESTS=True`` or a test runs inside
    ``transaction.atomic``).
    """
    try:
        with transaction.atomic():
            row = PaddleWebhookEvent.objects.create(
                paddle_event_id=metadata.event_id,
                event_type=metadata.event_type,
                signature=(signature_header or "")[:128],
                payload=payload,
                organization_id=metadata.org_id or "",
                subscription_id=metadata.subscription_id or "",
                billing_state_version_at_dispatch=snapshot_version,
                status=PaddleWebhookEvent.Status.RECEIVED,
            )
    except IntegrityError:
        existing = PaddleWebhookEvent.objects.filter(
            paddle_event_id=metadata.event_id,
        ).first()
        return existing, True
    return row, False


def process_payload(
    payload: dict,
    *,
    signature_header: str = "",
) -> PipelineResult:
    """End-to-end pipeline used by the synchronous webhook view.

    Caller is expected to have already verified the signature; this
    function focuses on idempotency + version-guarded mutation.
    """
    metadata = extract_event_metadata(payload)

    if not metadata.event_id:
        # Paddle should always send event_id; treat missing as a malformed
        # payload, but never 4xx (the upstream view returns 202 to stop
        # Paddle retrying — we just record + ignore).
        logger.warning(
            "Paddle webhook missing event_id; ignoring event_type=%s",
            metadata.event_type,
        )
        return PipelineResult(event=None, status="ignored", detail="missing_event_id")

    if not metadata.event_type:
        return PipelineResult(event=None, status="ignored", detail="missing_event_type")

    org, snapshot_version = _resolve_org_version(metadata.org_id)

    row, is_duplicate = _create_event_row(
        metadata,
        payload,
        signature_header,
        snapshot_version,
    )
    if is_duplicate:
        if row is not None:
            # Duplicates are an audit signal — record once but don't spam.
            AuditService.log(
                action="billing.webhook.duplicate",
                resource_type="paddle_webhook_event",
                resource_id=row.paddle_event_id,
                metadata={
                    "event_type": row.event_type,
                    "original_status": row.status,
                },
            )
        return PipelineResult(event=row, status="duplicate")

    assert row is not None  # mypy: create returned a row when not duplicate
    return _apply_event(row, metadata, org, snapshot_version)


def _apply_event(
    row: PaddleWebhookEvent,
    metadata: EventMetadata,
    org: Organization | None,
    snapshot_version: int | None,
) -> PipelineResult:
    """Inner step: dispatch under a transaction + re-check the version.

    Important: any "post-dispatch" bookkeeping (audit log, row.save with
    the new status) must run **outside** the inner atomic block.
    ``transaction.set_rollback(True)`` immediately blocks further queries
    inside that block (Django poisons the connection until the block exits),
    so we record the decision here and persist it after the ``with`` exits.
    """
    skip_reason: tuple[int | None, int | None] | None = None  # (snapshot, current)
    failure: Exception | None = None
    try:
        with transaction.atomic():
            dispatch_event(
                metadata.event_type,
                metadata.event_data,
                metadata.org_id,
            )
            if org is not None and snapshot_version is not None:
                current_version = (
                    Organization.objects.filter(pk=org.pk)
                    .values_list("billing_state_version", flat=True)
                    .first()
                )
                if current_version is not None and current_version != snapshot_version:
                    # Mark for rollback; defer the row.save until we're
                    # out of this atomic block (set_rollback freezes I/O).
                    transaction.set_rollback(True)
                    skip_reason = (snapshot_version, current_version)
    except Exception as exc:  # noqa: BLE001 — captured + audited below
        failure = exc

    if skip_reason is not None:
        snap, cur = skip_reason
        row.status = PaddleWebhookEvent.Status.SKIPPED
        row.error = (
            f"billing_state_version changed during dispatch "
            f"(snapshot={snap} current={cur})"
        )
        row.processed_at = timezone.now()
        row.save(update_fields=["status", "error", "processed_at"])
        AuditService.log(
            action="billing.webhook.skipped",
            resource_type="paddle_webhook_event",
            resource_id=row.paddle_event_id,
            organization=org,
            metadata={
                "event_type": metadata.event_type,
                "reason": "reset_race",
                "snapshot_version": snap,
                "current_version": cur,
            },
        )
        return PipelineResult(event=row, status="skipped")

    if failure is not None:
        row.status = PaddleWebhookEvent.Status.FAILED
        row.error = repr(failure)[:8000]
        row.processed_at = timezone.now()
        row.save(update_fields=["status", "error", "processed_at"])
        logger.exception(
            "Paddle webhook dispatch failed: %s",
            metadata.event_type,
        )
        AuditService.log(
            action="billing.webhook.failed",
            resource_type="paddle_webhook_event",
            resource_id=row.paddle_event_id,
            metadata={
                "event_type": metadata.event_type,
                "error": repr(failure)[:500],
            },
        )
        return PipelineResult(event=row, status="failed", detail=repr(failure))

    row.status = PaddleWebhookEvent.Status.ACCEPTED
    row.processed_at = timezone.now()
    row.save(update_fields=["status", "processed_at"])
    return PipelineResult(event=row, status="accepted")


def replay_event(row: PaddleWebhookEvent) -> PipelineResult:
    """Re-run dispatch for an existing event row.

    Used by the admin "Replay event" action and by support tooling.
    The replay bypasses the idempotency insert (we already have the row)
    but still respects the version guard against the *current* org state.
    """
    payload = row.payload or {}
    metadata = extract_event_metadata(payload)
    if not metadata.event_id:
        return PipelineResult(event=row, status="ignored", detail="missing_event_id")
    org, snapshot_version = _resolve_org_version(metadata.org_id)
    return _apply_event(row, metadata, org, snapshot_version)
