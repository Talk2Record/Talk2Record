from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

from talk2record.billing.models import Subscription
from talk2record.usage.models import AIUsage

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization
    from talk2record.records.models import Record


class AIUsageQuotaExceededError(RuntimeError):
    pass


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
        now = timezone.now()
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return AIUsage.objects.filter(
            organization=organization,
            created_at__gte=start_of_month,
        ).count()

    @staticmethod
    def monthly_usage_limit(organization: Organization) -> int:
        subscription = (
            Subscription.objects.filter(
                organization=organization,
                status=Subscription.Status.ACTIVE,
            )
            .select_related("plan")
            .first()
        )
        if subscription is not None:
            plan_limit = _extract_limit_from_features(subscription.plan.features)
            if plan_limit > 0:
                return plan_limit
        return int(getattr(settings, "AI_USAGE_MONTHLY_LIMIT_PER_ORG", 0))

    @staticmethod
    def enforce_monthly_usage_limit(organization: Organization) -> None:
        limit = UsageTrackingService.monthly_usage_limit(organization)
        if limit <= 0:
            return
        if UsageTrackingService.monthly_usage_count(organization) >= limit:
            msg = "Monthly AI usage quota exceeded for organization."
            raise AIUsageQuotaExceededError(msg)


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
