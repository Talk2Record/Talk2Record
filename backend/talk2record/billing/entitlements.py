"""Feature-flag & usage-limit lookup service backed by ``PlanEntitlement``.

Callers should use ``EntitlementService`` instead of peeking at the raw
subscription/plan JSON — the service hides the details of how plans map to
features and which subscription is active.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from talk2record.billing.models import (
    PlanEntitlement,
    Subscription,
)

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


@dataclass(frozen=True)
class Entitlement:
    feature_key: str
    enabled: bool
    limit: int
    period: str


class EntitlementService:
    """Resolve plan entitlements for an organisation."""

    @staticmethod
    def _active_subscription(organization: Organization) -> Subscription | None:
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

    @classmethod
    def list_for_organization(cls, organization: Organization) -> list[Entitlement]:
        subscription = cls._active_subscription(organization)
        if subscription is None:
            return []
        rows = PlanEntitlement.objects.filter(plan=subscription.plan)
        return [
            Entitlement(
                feature_key=row.feature_key,
                enabled=row.enabled,
                limit=row.limit,
                period=row.period,
            )
            for row in rows
        ]

    @classmethod
    def get(cls, organization: Organization, feature_key: str) -> Entitlement | None:
        subscription = cls._active_subscription(organization)
        if subscription is None:
            return None
        row = PlanEntitlement.objects.filter(
            plan=subscription.plan,
            feature_key=feature_key,
        ).first()
        if row is None:
            return None
        return Entitlement(
            feature_key=row.feature_key,
            enabled=row.enabled,
            limit=row.limit,
            period=row.period,
        )

    @classmethod
    def has_feature(cls, organization: Organization, feature_key: str) -> bool:
        entitlement = cls.get(organization, feature_key)
        return bool(entitlement and entitlement.enabled)

    @classmethod
    def get_limit(
        cls,
        organization: Organization,
        feature_key: str,
        default: int = 0,
    ) -> int:
        entitlement = cls.get(organization, feature_key)
        if entitlement is None or not entitlement.enabled:
            return default
        return int(entitlement.limit) or default
