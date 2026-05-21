from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

from talk2record.billing.entitlements import EntitlementService
from talk2record.billing.models import Subscription
from talk2record.usage.models import AIUsage

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization
    from talk2record.records.models import Record


# Feature key used by `PlanEntitlement` to express the per-cycle AI usage cap.
# Kept as a module-level constant so the admin, billing snapshot, and tests
# never disagree about which entitlement row drives the quota.
AI_USAGE_FEATURE_KEY = "ai.usage"


class AIUsageQuotaExceededError(RuntimeError):
    pass


@dataclass(frozen=True)
class UsageSummary:
    """Snapshot of an organization's metered usage for the current cycle.

    Returned by ``UsageTrackingService.usage_summary`` so the billing snapshot,
    the per-org admin review, and the frontend usage card all read from a
    single helper instead of recomputing limits independently.
    """

    feature_key: str
    used: int
    included: int  # 0 = unlimited / feature flag only
    percent_used: int  # 0-100, always 0 when `included == 0`
    period_start: datetime
    period_end: datetime
    plan_code: str | None
    billing_interval: str
    subscription_status: str | None


class UsageTrackingService:
    @staticmethod
    def log_ai_usage(  # noqa: PLR0913
        *,
        record: Record,
        provider: str,
        service_type: str,
        duration_seconds: float = 0,
        tokens_used: int = 0,
        cost_usd: Decimal = Decimal("0.00"),
    ) -> AIUsage:
        return AIUsage.objects.create(
            organization=record.organization,
            record=record,
            provider=provider,
            service_type=service_type,
            duration_seconds=duration_seconds,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

    @staticmethod
    def monthly_usage_count(organization: Organization) -> int:
        period_start, _ = _current_cycle(timezone.now())
        return AIUsage.objects.filter(
            organization=organization,
            created_at__gte=period_start,
        ).count()

    @staticmethod
    def monthly_usage_limit(organization: Organization) -> int:
        """Resolve the per-cycle AI usage cap.

        Resolution order (new in Phase 2):
          1. ``PlanEntitlement`` keyed by ``ai.usage`` for the active/trialing
             subscription — the new source of truth.
          2. Legacy ``Plan.features`` JSON (kept only for older seeds).
          3. ``AI_USAGE_MONTHLY_LIMIT_PER_ORG`` settings default (free tier).
        """

        entitlement_limit = EntitlementService.get_limit(
            organization, AI_USAGE_FEATURE_KEY,
        )
        if entitlement_limit > 0:
            return entitlement_limit

        subscription = _active_subscription(organization)
        if subscription is not None:
            plan_limit = _extract_limit_from_features(subscription.plan.features)
            if plan_limit > 0:
                return plan_limit
        return int(getattr(settings, "AI_USAGE_MONTHLY_LIMIT_PER_ORG", 0))

    @classmethod
    def usage_summary(cls, organization: Organization) -> UsageSummary:
        now = timezone.now()
        period_start, period_end = _current_cycle(now)
        used = cls.monthly_usage_count(organization)
        included = cls.monthly_usage_limit(organization)
        percent = 0
        if included > 0:
            percent = min(100, int(round((used / included) * 100)))

        subscription = _active_subscription(organization)
        return UsageSummary(
            feature_key=AI_USAGE_FEATURE_KEY,
            used=used,
            included=included,
            percent_used=percent,
            period_start=period_start,
            period_end=period_end,
            plan_code=subscription.plan.code if subscription else None,
            billing_interval=(
                subscription.billing_interval if subscription else "month"
            ),
            subscription_status=subscription.status if subscription else None,
        )

    @staticmethod
    def enforce_monthly_usage_limit(organization: Organization) -> None:
        limit = UsageTrackingService.monthly_usage_limit(organization)
        if limit <= 0:
            return
        if UsageTrackingService.monthly_usage_count(organization) >= limit:
            _publish_limit_exceeded(organization)
            msg = "Monthly AI usage quota exceeded for organization."
            raise AIUsageQuotaExceededError(msg)


def _active_subscription(organization: Organization) -> Subscription | None:
    """Return the active or trialing subscription for ``organization``.

    Both states grant plan entitlements — trialing customers should see the
    same caps as paying customers so the UI and quota enforcement stay in
    sync once the trial converts.
    """

    return (
        Subscription.objects.filter(
            organization=organization,
            status__in=(
                Subscription.Status.ACTIVE,
                Subscription.Status.TRIALING,
            ),
        )
        .select_related("plan")
        .first()
    )


def _current_cycle(now: datetime) -> tuple[datetime, datetime]:
    """Return ``(period_start, period_end)`` for the calendar month of ``now``."""

    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(
            year=period_start.year + 1, month=1,
        )
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return period_start, period_end


def _publish_limit_exceeded(organization: Organization) -> None:
    from talk2record.events import DomainEvent, publish_after_commit
    from talk2record.events.names import BILLING_LIMIT_EXCEEDED

    publish_after_commit(
        DomainEvent(
            name=BILLING_LIMIT_EXCEEDED,
            organization_id=organization.pk,
            user_id=None,
            resource_type="organization",
            resource_id=str(organization.pk),
            metadata={"reason": "monthly_ai_usage_quota_exceeded"},
        ),
    )


def _extract_limit_from_features(features: object) -> int:
    if isinstance(features, dict):
        value = features.get("ai_usage_monthly_limit", 0)
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if isinstance(features, list):
        for item in features:
            if not isinstance(item, str):
                continue
            prefix = "ai_usage_monthly_limit:"
            if item.startswith(prefix):
                try:
                    return int(item.removeprefix(prefix))
                except ValueError:
                    return 0
    return 0
