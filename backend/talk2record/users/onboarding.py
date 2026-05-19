from __future__ import annotations

from typing import TYPE_CHECKING

from talk2record.billing.models import Subscription

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


def is_company_setup_complete(organization: Organization | None) -> bool:
    if organization is None:
        return False
    return bool(organization.profile_setup_completed)


def has_active_subscription(organization: Organization | None) -> bool:
    if organization is None:
        return False
    return Subscription.objects.filter(
        organization=organization,
        status__in=[
            Subscription.Status.TRIALING,
            Subscription.Status.ACTIVE,
            Subscription.Status.PAST_DUE,
        ],
    ).exists()
