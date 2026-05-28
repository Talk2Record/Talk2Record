"""Admin-only views that power ``/admin/billing/dashboard/``.

The Unfold admin already ships an app-level index at ``/admin/billing/`` that
just lists registered changelists. This module adds an operational dashboard
*next to* that index with the metrics support / ops actually need:

- MRR / ARR / Active / Trialing (ending soon) / Past-due / Failed payments /
  Revenue this month / Voluntary churn rate
- Plan distribution (subs per plan × interval)
- Trialing subscriptions ending soon
- Recent transactions (last 20)
- Top organizations by spend (90d)
- "Sync all from Paddle" quick action (enqueues push+pull sync task)

Source of truth note: every number here is derived from local Django tables
written by Paddle webhooks (control-plane view of the financial ledger).
Re-running ``Sync all from Paddle`` refreshes stale rows. The queued task also
pushes local active plan/price catalog rows to Paddle before pulling
subscriptions so seeded billing config can be published from admin.
"""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal
from typing import Any

from django.contrib import admin
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count
from django.db.models import DecimalField
from django.db.models import F
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import PaddleWebhookEvent
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.recovery_service import BillingRecoveryService
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)
PADDLE_SYNC_SUMMARY_CACHE_KEY = "billing:paddle_sync:last_summary"

# Recurring-revenue snapshot: only subs that are currently billing.
_BILLING_STATUSES = (Subscription.Status.ACTIVE, Subscription.Status.TRIALING)
_TRIAL_SOON_DAYS = 7
_FAILED_WINDOW_DAYS = 30
_TOP_ORGS_WINDOW_DAYS = 90


def _to_decimal(value: object) -> Decimal:
    """Coerce a Django aggregate result to ``Decimal``, defaulting to zero."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _monthly_amount(amount: Decimal, interval: str) -> Decimal:
    """Normalise a subscription amount to a monthly figure for MRR math.

    Annual subs contribute 1/12 of their price to MRR; one-off prices contribute
    nothing (they aren't recurring revenue).
    """
    if interval == PlanPrice.Interval.YEAR:
        return amount / Decimal("12")
    if interval == PlanPrice.Interval.ONE_TIME:
        return Decimal("0")
    return amount


def _compute_mrr_arr() -> tuple[Decimal, Decimal]:
    """Sum monthly-normalised amounts across all *currently billing* subs."""
    rows = Subscription.objects.filter(status__in=_BILLING_STATUSES).values_list(
        "amount",
        "billing_interval",
    )
    mrr = sum((_monthly_amount(_to_decimal(a), i) for a, i in rows), Decimal("0"))
    return mrr, mrr * Decimal("12")


def _compute_kpis(now: datetime.datetime) -> list[dict[str, Any]]:
    """Build the KPI card payload."""
    mrr, arr = _compute_mrr_arr()

    soon = now + datetime.timedelta(days=_TRIAL_SOON_DAYS)
    trialing_soon = Subscription.objects.filter(
        status=Subscription.Status.TRIALING,
        current_period_end__gt=now,
        current_period_end__lte=soon,
    ).count()

    active = Subscription.objects.filter(
        status=Subscription.Status.ACTIVE,
    ).count()
    past_due = Subscription.objects.filter(
        status=Subscription.Status.PAST_DUE,
    ).count()

    failed_since = now - datetime.timedelta(days=_FAILED_WINDOW_DAYS)
    failed_payments = Transaction.objects.filter(
        status=Transaction.Status.FAILED,
        issued_at__gte=failed_since,
    ).count()

    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    revenue_this_month = _to_decimal(
        Transaction.objects.filter(
            status=Transaction.Status.PAID,
            paid_at__gte=month_start,
        ).aggregate(
            total=Coalesce(Sum("amount"), Decimal("0"), output_field=DecimalField()),
        )["total"],
    )

    # Voluntary churn (rolling 30d): canceled subs / canceled + still-active
    # at the start of the window. We use canceled_at as the source of truth
    # and fall back to created_at when missing (best-effort, see Phase 3
    # webhook hardening). This is a directional metric — not GAAP-accurate.
    churn_since = now - datetime.timedelta(days=_FAILED_WINDOW_DAYS)
    canceled_30d = Subscription.objects.filter(
        status=Subscription.Status.CANCELED,
        canceled_at__gte=churn_since,
    ).count()
    base = active + canceled_30d
    churn_pct = (canceled_30d / base * 100) if base else 0

    return [
        {
            "title": _("Monthly Recurring Revenue"),
            "metric": f"${mrr:,.2f}",
            "footer": _("Active + trialing, normalised to monthly"),
        },
        {
            "title": _("Annual Run Rate"),
            "metric": f"${arr:,.2f}",
            "footer": _("MRR × 12"),
        },
        {
            "title": _("Active subscriptions"),
            "metric": f"{active}",
            "footer": None,
        },
        {
            "title": _("Trialing — ending in 7 days"),
            "metric": f"{trialing_soon}",
            "footer": _("Card on file, first paid charge imminent"),
        },
        {
            "title": _("Past-due"),
            "metric": f"{past_due}",
            "footer": _("Payment retries in flight"),
        },
        {
            "title": _("Failed payments (30d)"),
            "metric": f"{failed_payments}",
            "footer": _("Transactions with status=failed"),
        },
        {
            "title": _("Revenue this month"),
            "metric": f"${revenue_this_month:,.2f}",
            "footer": _("Paid transactions, paid_at this month"),
        },
        {
            "title": _("Voluntary churn (30d)"),
            "metric": f"{churn_pct:.1f}%",
            "footer": _("Canceled / (Active + Canceled in 30d)"),
        },
    ]


def _plan_distribution() -> list[dict[str, Any]]:
    """Subscription count grouped by plan × interval (active + trialing only)."""
    rows = (
        Subscription.objects.filter(status__in=_BILLING_STATUSES)
        .values(
            "plan__code",
            "plan__name",
            "billing_interval",
        )
        .annotate(count=Count("id"))
        .order_by("plan__code", "billing_interval")
    )
    return [
        {
            "plan_code": row["plan__code"],
            "plan_name": row["plan__name"],
            "interval": row["billing_interval"],
            "count": row["count"],
        }
        for row in rows
    ]


def _trialing_soon(now: datetime.datetime) -> list[dict[str, Any]]:
    soon = now + datetime.timedelta(days=_TRIAL_SOON_DAYS)
    rows = (
        Subscription.objects.filter(
            status=Subscription.Status.TRIALING,
            current_period_end__gt=now,
            current_period_end__lte=soon,
        )
        .select_related("organization", "plan")
        .order_by("current_period_end")
    )
    out: list[dict[str, Any]] = []
    for sub in rows:
        delta = sub.current_period_end - now if sub.current_period_end else None
        out.append(
            {
                "id": sub.pk,
                "organization": sub.organization.name,
                "organization_id": sub.organization_id,
                "plan": sub.plan.name,
                "interval": sub.billing_interval,
                "trial_ends_at": sub.current_period_end,
                "days_left": delta.days if delta else None,
                "change_url": reverse(
                    "admin_billing_organization_review",
                    args=[sub.organization_id],
                ),
                "subscription_change_url": reverse(
                    "admin:billing_subscription_change",
                    args=[sub.pk],
                ),
            },
        )
    return out


def _recent_transactions(limit: int = 20) -> list[Transaction]:
    return list(
        Transaction.objects.select_related(
            "subscription",
            "subscription__organization",
            "subscription__plan",
        ).order_by("-issued_at")[:limit],
    )


def _top_orgs_by_spend(now: datetime.datetime) -> list[dict[str, Any]]:
    since = now - datetime.timedelta(days=_TOP_ORGS_WINDOW_DAYS)
    rows = (
        Transaction.objects.filter(
            status=Transaction.Status.PAID,
            paid_at__gte=since,
        )
        .values(
            org_id=F("subscription__organization_id"),
            org_name=F("subscription__organization__name"),
            org_slug=F("subscription__organization__slug"),
        )
        .annotate(
            spend=Coalesce(Sum("amount"), Decimal("0"), output_field=DecimalField()),
            tx_count=Count("id"),
        )
        .order_by("-spend")[:10]
    )
    return [dict(row) for row in rows]


def billing_dashboard_view(request):
    """Render the ``/admin/billing/dashboard/`` Unfold page."""
    now = timezone.now()
    last_sync_summary = cache.get(PADDLE_SYNC_SUMMARY_CACHE_KEY)
    context = {
        **admin.site.each_context(request),
        "title": _("Billing dashboard"),
        "now": now,
        "kpi_cards": _compute_kpis(now),
        "plan_distribution": _plan_distribution(),
        "trialing_soon": _trialing_soon(now),
        "recent_transactions": _recent_transactions(),
        "top_orgs": _top_orgs_by_spend(now),
        "subscription_changelist_url": reverse(
            "admin:billing_subscription_changelist",
        ),
        "transaction_changelist_url": reverse(
            "admin:billing_transaction_changelist",
        ),
        "plan_changelist_url": reverse("admin:billing_plan_changelist"),
        "plan_price_changelist_url": reverse(
            "admin:billing_planprice_changelist",
        ),
        "paddle_settings_changelist_url": reverse(
            "admin:billing_paddlesettings_changelist",
        ),
        "test_paddle_url": reverse("admin_test_paddle_connection"),
        "sync_all_url": reverse("admin_billing_sync_all"),
        "last_sync_summary": last_sync_summary,
    }
    return render(request, "admin/billing/dashboard.html", context)


# ---------------------------------------------------------------------------
# Per-org Billing Recovery review + reset (Phase 5)
# ---------------------------------------------------------------------------


def _recent_webhook_events(organization_id: int, limit: int = 20):
    return list(
        PaddleWebhookEvent.objects.filter(
            organization_id=str(organization_id),
        ).order_by("-received_at")[:limit],
    )


def _org_subscription_rows(organization: Organization) -> list[dict[str, Any]]:
    """Render-friendly snapshot of an org's subscriptions for the review page."""
    rows = []
    for sub in (
        Subscription.objects.filter(organization=organization)
        .select_related("plan", "price")
        .order_by("-created_at")
    ):
        rows.append(
            {
                "id": sub.pk,
                "plan_name": sub.plan.name if sub.plan_id else "",
                "plan_code": sub.plan.code if sub.plan_id else "",
                "status": sub.status,
                "billing_interval": sub.billing_interval,
                "amount": sub.amount,
                "currency": sub.currency,
                "provider_subscription_id": sub.provider_subscription_id,
                "paddle_customer_id": sub.paddle_customer_id,
                "current_period_end": sub.current_period_end,
                "canceled_at": sub.canceled_at,
                "change_url": reverse(
                    "admin:billing_subscription_change",
                    args=[sub.pk],
                ),
            },
        )
    return rows


def billing_organization_review_view(request, organization_id: int):
    """Per-org review page used by support to inspect billing state.

    Surfaces: subscriptions + version, entitlements, recent transactions,
    Paddle customer id (deep-link), recent ``PaddleWebhookEvent`` rows so
    support can see what Paddle told us, and the "Reset billing" trigger.
    """
    organization = get_object_or_404(Organization, pk=organization_id)

    subs = _org_subscription_rows(organization)
    recent_txs = list(
        Transaction.objects.filter(
            subscription__organization=organization,
        )
        .select_related("subscription", "subscription__plan")
        .order_by("-issued_at")[:20],
    )
    webhook_events = _recent_webhook_events(organization.pk)
    entitlements = EntitlementService.list_for_organization(organization)

    paddle_customer_id = next(
        (s["paddle_customer_id"] for s in subs if s.get("paddle_customer_id")),
        "",
    )

    context = {
        **admin.site.each_context(request),
        "title": _("Billing Recovery — %(name)s") % {"name": organization.name},
        "organization": organization,
        "subscriptions": subs,
        "recent_transactions": recent_txs,
        "webhook_events": webhook_events,
        "entitlements": entitlements,
        "paddle_customer_id": paddle_customer_id,
        "reset_url": reverse(
            "admin_billing_reset_organization",
            args=[organization.pk],
        ),
        "dashboard_url": reverse("admin_billing_dashboard"),
    }
    return render(request, "admin/billing/organization.html", context)


def billing_reset_organization_view(request, organization_id: int):
    """POST handler for the per-org "Reset billing" button.

    ``reason`` is required and surfaced as a form-level error. Optionally
    accepts ``also_reset_onboarding=on``. Delegates the heavy lifting to
    :class:`BillingRecoveryService`.
    """
    if request.method != "POST":
        return redirect(
            reverse(
                "admin_billing_organization_review",
                args=[organization_id],
            ),
        )

    organization = get_object_or_404(Organization, pk=organization_id)
    reason = (request.POST.get("reason") or "").strip()
    also_reset_onboarding = request.POST.get("also_reset_onboarding") == "on"

    if not reason:
        messages.error(
            request,
            _("A reason is required to reset billing for an organisation."),
        )
        return redirect(
            reverse(
                "admin_billing_organization_review",
                args=[organization.pk],
            ),
        )

    try:
        report = BillingRecoveryService().reset(
            organization,
            actor=request.user,
            reason=reason,
            also_reset_onboarding=also_reset_onboarding,
        )
    except Exception as exc:
        logger.exception("BillingRecoveryService failed for org=%s", organization.pk)
        messages.error(
            request,
            _("Billing reset failed: %(detail)s") % {"detail": str(exc)},
        )
        return redirect(
            reverse(
                "admin_billing_organization_review",
                args=[organization.pk],
            ),
        )

    if report.paddle_errors:
        messages.warning(
            request,
            _(
                "Billing reset completed locally, but %(count)d Paddle calls "
                "reported errors — see audit log for details.",
            )
            % {"count": len(report.paddle_errors)},
        )
    else:
        messages.success(
            request,
            _("Billing reset for %(name)s completed (state v%(v)s).")
            % {
                "name": organization.name,
                "v": report.new_billing_state_version,
            },
        )
    return redirect(
        reverse(
            "admin_billing_organization_review",
            args=[organization.pk],
        ),
    )


def billing_sync_all_view(request):
    """Enqueue push+pull Paddle sync for catalog and subscriptions.

    POST only — admin-protected by ``admin.site.admin_view`` wrapper in
    ``config/urls.py``. Returns a redirect with a flash message.
    """
    if request.method != "POST":
        return redirect(reverse("admin_billing_dashboard"))

    # Local import to avoid pulling Celery into module import time
    # (keeps the dashboard view fast and testable without a broker).
    from talk2record.billing.tasks import sync_paddle_state

    pending_subs = Subscription.objects.exclude(provider_subscription_id="").count()
    active_plans = Plan.objects.filter(is_active=True).count()
    active_prices = PlanPrice.objects.filter(active=True).count()
    active_entitlements = PlanEntitlement.objects.filter(
        plan__is_active=True,
        enabled=True,
    ).count()
    try:
        task = sync_paddle_state.delay()
        cache.set(
            PADDLE_SYNC_SUMMARY_CACHE_KEY,
            {
                "status": "queued",
                "queued_at": timezone.now().isoformat(),
                "task_id": getattr(task, "id", ""),
                "plans_pushed": 0,
                "prices_pushed": 0,
                "entitlements_published": 0,
                "synced": 0,
                "failed": 0,
                "skipped": 0,
            },
            timeout=7 * 24 * 60 * 60,
        )
    except Exception as exc:
        logger.exception("Failed to enqueue Paddle sync-all task")
        messages.error(
            request,
            _("Could not enqueue Paddle sync: %(detail)s") % {"detail": str(exc)},
        )
        return redirect(reverse("admin_billing_dashboard"))

    messages.success(
        request,
        _(
            "Queued Paddle sync: %(plans)d plans, %(prices)d prices, "
            "%(entitlements)d entitlements, %(subs)d subscriptions.",
        )
        % {
            "plans": active_plans,
            "prices": active_prices,
            "entitlements": active_entitlements,
            "subs": pending_subs,
        },
    )
    return redirect(reverse("admin_billing_dashboard"))
