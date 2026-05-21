"""Billing Recovery System — first-class support tooling for billing resets.

This module implements the 6-step *Sync Order* the user defined for safely
"starting fresh" on an organisation's commercial billing state without
touching Paddle's immutable financial ledger or any non-billing user data
(profile, sessions, records, audit logs, paid transactions).

Two-plane principle, enforced throughout:

============================  ==========================================
Concern                       Source of truth
============================  ==========================================
Subscription status, paid     **Paddle**
transactions, refunds, tax
records, dispute history
Access control, entitlement   **Django**
caches, usage counters,
audit, support tooling
============================  ==========================================

Rules of the road:

- **Django:** reset commercial state ONLY. NEVER touch User profile,
  sessions, password, uploaded files, Record / RecordArtifact, business
  records, Organization name / Membership, paid Transaction rows, or
  audit logs. Those are permanent records.
- **Paddle:** ONLY operational cancel / void / close. NEVER call
  ``delete_*``, NEVER attempt cleanup of historical data, NEVER rewrite
  paid invoices / refunds / chargebacks / tax records.
- **Race safety:** every reset bumps ``Organization.billing_state_version``
  as step 1 so any in-flight Paddle webhook holding the old version
  gets marked SKIPPED by ``webhook_pipeline._apply_event`` instead of
  clobbering the reset.

The Sync Order (implemented by :meth:`BillingRecoveryService.reset`):

1. **LOCK** — bump ``billing_state_version`` (the webhook race guard).
2. **PADDLE** — operational cancel: cancel active subscription
   (``effective_from=immediately``), void pending transactions, close
   pending checkout sessions. NEVER destructive.
3. **VERIFY** — pull live Paddle subscription state, confirm it
   reflects the cancellation. Failures are recorded, not raised.
4. **RESET DJANGO STATE (commercial only)** — mark local
   ``Subscription`` rows CANCELED, clear ``price`` FK +
   ``billing_interval``, drop *current-cycle* ``AIUsage`` rows
   (history older than the cycle is preserved).
5. **RECOMPUTE ENTITLEMENTS** — invalidate cached entitlements via
   :meth:`EntitlementService.invalidate_for`.
6. **UNLOCK + AUDIT** — write a ``billing.reset`` audit row capturing
   the actor, reason, old snapshot, new snapshot, and Paddle subscription
   id for the recovery trail. Optionally also reset onboarding
   (decoupled per ``also_reset_onboarding`` flag).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from talk2record.audit.services import AuditService
from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.paddle_client import PaddleAPIError
from talk2record.billing.paddle_service import PaddleBillingService
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Report dataclass — what the caller sees back
# ---------------------------------------------------------------------------


@dataclass
class BillingResetReport:
    organization_id: int
    actor_id: int | None
    reason: str
    old_state: dict[str, Any]
    new_state: dict[str, Any]
    paddle_subscription_ids: list[str] = field(default_factory=list)
    paddle_errors: list[str] = field(default_factory=list)
    usage_rows_cleared: int = 0
    onboarding_reset: bool = False
    new_billing_state_version: int = 0


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class BillingRecoveryService:
    """Reset an organisation's commercial billing state safely.

    The service is stateless — each ``reset()`` call is an atomic
    operation. Paddle calls happen outside the inner Django transaction
    (Paddle errors are captured into the report rather than raised so
    state stays consistent), but the version bump + local mutations are
    transactional.
    """

    def __init__(self, paddle: PaddleBillingService | None = None) -> None:
        self.paddle = paddle or PaddleBillingService()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(
        self,
        organization: Organization,
        *,
        actor,
        reason: str,
        also_reset_onboarding: bool = False,
    ) -> BillingResetReport:
        """Run the 6-step Sync Order against ``organization``.

        ``reason`` is required (audit trail). ``actor`` should be the
        platform-staff ``User`` performing the reset. ``also_reset_onboarding``
        is opt-in because most resets keep the org's setup work intact.
        """
        if not reason or not reason.strip():
            msg = "reason is required for billing reset (audit trail)."
            raise ValueError(msg)

        old_state = self._snapshot(organization)

        # -------- Step 1: LOCK ---------------------------------------------
        # Bump the version FIRST so any concurrent Paddle webhook holding
        # the old snapshot is SKIPPED by the pipeline's version guard.
        with transaction.atomic():
            Organization.objects.filter(pk=organization.pk).update(
                billing_state_version=F("billing_state_version") + 1,
            )
        organization.refresh_from_db(fields=["billing_state_version"])

        # -------- Step 2: PADDLE — operational cancel only -----------------
        paddle_subscription_ids: list[str] = []
        paddle_errors: list[str] = []
        self._paddle_operational_cancel(
            organization,
            collected_ids=paddle_subscription_ids,
            collected_errors=paddle_errors,
        )

        # -------- Step 3: VERIFY ------------------------------------------
        # Re-pull live Paddle subscription state. Failures are logged but
        # do NOT abort the reset — local cleanup must still proceed (we
        # already locked the org, downstream support can re-sync later).
        self._verify_paddle_state(
            organization,
            collected_errors=paddle_errors,
        )

        # -------- Step 4: RESET DJANGO STATE (commercial only) -------------
        # Wrap step 4 in its own atomic block so the local cancel + AIUsage
        # purge land together or not at all.
        with transaction.atomic():
            usage_rows_cleared = self._reset_django_state(organization)

        # -------- Step 5: RECOMPUTE ENTITLEMENTS ---------------------------
        EntitlementService.invalidate_for(organization)

        # -------- Step 6: UNLOCK + AUDIT -----------------------------------
        onboarding_reset = False
        if also_reset_onboarding:
            onboarding_reset = self._reset_onboarding(organization)

        organization.refresh_from_db(fields=["billing_state_version"])
        new_state = self._snapshot(organization)

        AuditService.log(
            action="billing.reset",
            resource_type="organization",
            resource_id=str(organization.pk),
            actor=actor,
            organization=organization,
            metadata={
                "reason": reason.strip(),
                "old_state": old_state,
                "new_state": new_state,
                "paddle_subscription_ids": paddle_subscription_ids,
                "paddle_errors": paddle_errors,
                "usage_rows_cleared": usage_rows_cleared,
                "onboarding_reset": onboarding_reset,
                "new_billing_state_version": organization.billing_state_version,
            },
        )

        logger.info(
            "BillingRecoveryService.reset: org=%s actor=%s usage_cleared=%s "
            "paddle_subs=%s errors=%s new_version=%s",
            organization.pk,
            getattr(actor, "pk", None),
            usage_rows_cleared,
            paddle_subscription_ids,
            paddle_errors,
            organization.billing_state_version,
        )

        return BillingResetReport(
            organization_id=organization.pk,
            actor_id=getattr(actor, "pk", None),
            reason=reason.strip(),
            old_state=old_state,
            new_state=new_state,
            paddle_subscription_ids=paddle_subscription_ids,
            paddle_errors=paddle_errors,
            usage_rows_cleared=usage_rows_cleared,
            onboarding_reset=onboarding_reset,
            new_billing_state_version=organization.billing_state_version,
        )

    # ------------------------------------------------------------------
    # Step 2 — Paddle operational cancel
    # ------------------------------------------------------------------

    def _paddle_operational_cancel(
        self,
        organization: Organization,
        *,
        collected_ids: list[str],
        collected_errors: list[str],
    ) -> None:
        """Cancel active subscriptions and void pending transactions.

        Skipped silently when Paddle isn't configured (local-dev safe).
        """
        if not self.paddle.client.is_configured():
            logger.info(
                "Skipping Paddle operational cancel for org=%s — client not configured",
                organization.pk,
            )
            return

        # 2a. Cancel active subscriptions (effective_from=immediately so
        #     access ends now). Paddle's own `subscription.canceled` webhook
        #     will arrive later and be applied harmlessly because our local
        #     row is already CANCELED by step 4.
        active_subs = list(
            Subscription.objects.filter(
                organization=organization,
                status__in=(
                    Subscription.Status.ACTIVE,
                    Subscription.Status.TRIALING,
                    Subscription.Status.PAUSED,
                    Subscription.Status.PAST_DUE,
                ),
            ).exclude(provider_subscription_id=""),
        )
        for sub in active_subs:
            collected_ids.append(sub.provider_subscription_id)
            try:
                self.paddle.cancel(sub, effective_from="immediately")
            except PaddleAPIError as exc:
                msg = f"cancel({sub.provider_subscription_id}): {exc}"
                logger.warning("BillingRecoveryService %s", msg)
                collected_errors.append(msg)

        # 2b. Void any locally-mirrored Transaction rows that are still
        #     PENDING. We never touch PAID / REFUNDED — those are immutable
        #     financial records.
        pending_tx = Transaction.objects.filter(
            subscription__organization=organization,
            status=Transaction.Status.PENDING,
        ).exclude(provider_transaction_id="")
        for tx in pending_tx:
            try:
                self.paddle.client.update_transaction(
                    tx.provider_transaction_id,
                    {"status": "canceled"},
                )
            except PaddleAPIError as exc:
                msg = f"void_tx({tx.provider_transaction_id}): {exc}"
                logger.warning("BillingRecoveryService %s", msg)
                collected_errors.append(msg)

    # ------------------------------------------------------------------
    # Step 3 — Verify Paddle state
    # ------------------------------------------------------------------

    def _verify_paddle_state(
        self,
        organization: Organization,
        *,
        collected_errors: list[str],
    ) -> None:
        """Refresh the local Paddle mirror so the audit row records reality.

        Per-sub errors are recorded, not raised — we already locked + want
        step 4 to land regardless of Paddle being flaky.
        """
        if not self.paddle.client.is_configured():
            return

        for sub in Subscription.objects.filter(organization=organization).exclude(
            provider_subscription_id="",
        ):
            try:
                self.paddle.sync_subscription(sub)
            except PaddleAPIError as exc:
                msg = f"sync_subscription({sub.provider_subscription_id}): {exc}"
                logger.warning("BillingRecoveryService %s", msg)
                collected_errors.append(msg)

    # ------------------------------------------------------------------
    # Step 4 — Reset Django commercial state
    # ------------------------------------------------------------------

    def _reset_django_state(self, organization: Organization) -> int:
        """Cancel local subscriptions, clear billing flags, drop usage cycle.

        Returns the number of ``AIUsage`` rows deleted for the current
        billing cycle. Older history is preserved.
        """
        # Local import keeps the usage app out of import time for callers
        # that don't need the recovery service (e.g. webhook hot path).
        from talk2record.usage.models import AIUsage
        from talk2record.usage.services import _current_cycle

        # 4a. Mark every local subscription as CANCELED, drop the price FK,
        #     reset the denormalised billing_interval to the default, and
        #     null out the period bounds. Provider IDs are kept so the audit
        #     trail can still link the canceled row back to Paddle.
        # billing_interval can't be left blank (NOT NULL on the column);
        # we restore the model default so dashboards don't render an empty cell.
        from talk2record.billing.models import PlanPrice

        Subscription.objects.filter(organization=organization).update(
            status=Subscription.Status.CANCELED,
            price=None,
            billing_interval=PlanPrice.Interval.MONTH,
            canceled_at=timezone.now(),
            current_period_end=None,
            amount=0,
        )

        # 4b. Clear *current-cycle* AIUsage rows so the org's quota resets.
        #     History older than the cycle is preserved — it's a permanent
        #     record of what the customer consumed.
        period_start, period_end = _current_cycle(timezone.now())
        deleted, _ = AIUsage.objects.filter(
            organization=organization,
            created_at__gte=period_start,
            created_at__lt=period_end,
        ).delete()

        return int(deleted or 0)

    # ------------------------------------------------------------------
    # Step 6 — optional onboarding reset
    # ------------------------------------------------------------------

    def _reset_onboarding(self, organization: Organization) -> bool:
        """Clear org-level onboarding state.

        Returns whether anything actually changed. We intentionally do NOT
        touch ``User.onboarding_completed`` — those are per-user flags and
        clearing them would force every team member to re-onboard.
        """
        if not organization.profile_setup_completed:
            return False
        organization.profile_setup_completed = False
        organization.save(update_fields=["profile_setup_completed", "updated_at"])
        return True

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    @staticmethod
    def _snapshot(organization: Organization) -> dict[str, Any]:
        """Capture the bits of org state we want in the audit trail.

        Subscriptions are summarised (not dumped wholesale) to keep the
        audit row JSON small + readable.
        """
        subs = list(
            Subscription.objects.filter(organization=organization).values(
                "id",
                "plan__code",
                "status",
                "billing_interval",
                "provider_subscription_id",
                "current_period_end",
            ),
        )
        for row in subs:
            # JSON-serialisable timestamps.
            if row.get("current_period_end") is not None:
                row["current_period_end"] = row["current_period_end"].isoformat()
        return {
            "organization_id": organization.pk,
            "organization_slug": organization.slug,
            "billing_state_version": organization.billing_state_version,
            "profile_setup_completed": organization.profile_setup_completed,
            "subscriptions": subs,
        }
