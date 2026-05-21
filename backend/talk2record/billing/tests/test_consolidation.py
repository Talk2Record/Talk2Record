"""Phase 7 — consolidation coverage.

Plugs the remaining test gaps surfaced after Phases 0-6 shipped:

- **Interval-aware change-plan** (Phase 1): same plan + different interval
  is a valid *upgrade path*, not a 400; the interval must be forwarded
  through to ``PaddleBillingService.change_plan`` so Paddle gets the
  right ``PlanPrice``.
- **Entitlement-driven usage** (Phase 2): ``monthly_usage_limit`` should
  prefer ``PlanEntitlement`` over the legacy ``Plan.features`` JSON, and
  ``usage_summary`` should return a fully populated ``UsageSummary``.
"""

from __future__ import annotations

from decimal import Decimal
from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient


# ---------------------------------------------------------------------------
# Phase 1 — change-plan interval contract
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_change_plan_accepts_interval_and_propagates_to_service(
    workspace_user, subscription, plan,
):
    """``change-plan`` must forward ``interval`` to ``PaddleBillingService.change_plan``.

    The frontend toggle posts ``interval="year"``; the view's job is to
    serialize and pass it through so :meth:`PaddleBillingService.change_plan`
    can select the right ``PlanPrice`` row.
    """
    from talk2record.billing.models import Plan
    from talk2record.billing.models import PlanPrice

    starter, _ = Plan.objects.get_or_create(
        code="starter",
        defaults={
            "name": "Starter",
            "base_price": Decimal("19.00"),
            "currency": "USD",
            "region": "US",
            "features": [],
        },
    )
    # Publish both monthly + annual on the target plan so the interval
    # actually has somewhere to point.
    PlanPrice.objects.update_or_create(
        plan=starter,
        interval="month",
        currency="USD",
        defaults={
            "amount": Decimal("19.00"),
            "active": True,
            "paddle_price_id": "pri_starter_monthly",
        },
    )
    PlanPrice.objects.update_or_create(
        plan=starter,
        interval="year",
        currency="USD",
        defaults={
            "amount": Decimal("190.00"),
            "active": True,
            "paddle_price_id": "pri_starter_annual",
        },
    )

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True
        mock_service.change_plan.return_value = type(
            "R",
            (),
            {"status": "updated", "plan_code": "starter"},
        )()

        response = client.post(
            reverse("api:billing-change-plan"),
            {
                "plan": "starter",
                "interval": "year",
                "acceptedBillingTerms": True,
            },
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    mock_service.change_plan.assert_called_once()
    call_kwargs = mock_service.change_plan.call_args.kwargs
    assert call_kwargs["new_plan"].code == "starter"
    assert call_kwargs["interval"] == "year"


@pytest.mark.django_db
def test_change_plan_same_plan_different_interval_is_allowed(
    workspace_user, subscription,
):
    """Switching cadence on the same plan must NOT be a 400.

    Pre-Phase-1 the view treated same-plan as the no-op case. Now that we
    track ``billing_interval``, a month → year switch on the same plan is
    a legitimate upgrade we should accept.
    """
    from talk2record.billing.models import PlanPrice

    # Ensure the annual price exists on the current plan.
    PlanPrice.objects.update_or_create(
        plan=subscription.plan,
        interval="year",
        currency="USD",
        defaults={
            "amount": Decimal("490.00"),
            "active": True,
            "paddle_price_id": "pri_growth_annual",
        },
    )
    # The subscription fixture defaults to billing_interval="month".
    subscription.billing_interval = "month"
    subscription.save(update_fields=["billing_interval"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True
        mock_service.change_plan.return_value = type(
            "R",
            (),
            {"status": "updated", "plan_code": subscription.plan.code},
        )()

        response = client.post(
            reverse("api:billing-change-plan"),
            {
                "plan": subscription.plan.code,
                "interval": "year",
                "acceptedBillingTerms": True,
            },
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    mock_service.change_plan.assert_called_once()
    assert mock_service.change_plan.call_args.kwargs["interval"] == "year"


@pytest.mark.django_db
def test_change_plan_same_plan_same_interval_still_returns_400(
    workspace_user, subscription,
):
    """No-op (same plan AND same interval) must still be rejected.

    Guards against accidentally turning every duplicate click into a Paddle
    API call.
    """
    subscription.billing_interval = "month"
    subscription.save(update_fields=["billing_interval"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service_cls.return_value.client.is_configured.return_value = True

        response = client.post(
            reverse("api:billing-change-plan"),
            {
                "plan": subscription.plan.code,
                "interval": "month",
                "acceptedBillingTerms": True,
            },
            format="json",
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST


# ---------------------------------------------------------------------------
# Phase 2 — entitlement-driven usage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_monthly_usage_limit_prefers_plan_entitlement_over_features_json(
    organization, subscription,
):
    """``PlanEntitlement.ai.usage`` must win over ``Plan.features`` JSON.

    The legacy resolver read the limit out of ``Plan.features``; Phase 2
    moved entitlements to a first-class model. We assert that a different
    value in features JSON is ignored when an entitlement row exists.
    """
    from talk2record.billing.models import PlanEntitlement
    from talk2record.usage.services import UsageTrackingService

    # Legacy JSON limit (should be ignored once entitlement is present).
    subscription.plan.features = ["ai_usage_monthly_limit:999"]
    subscription.plan.save(update_fields=["features"])

    PlanEntitlement.objects.update_or_create(
        plan=subscription.plan,
        feature_key="ai.usage",
        defaults={"enabled": True, "limit": 2500, "period": "monthly"},
    )

    assert UsageTrackingService.monthly_usage_limit(organization) == 2500


@pytest.mark.django_db
def test_monthly_usage_limit_falls_back_to_features_json(
    organization, subscription, settings,
):
    """When no ``PlanEntitlement`` row exists, the legacy resolver kicks in.

    Ensures we don't regress older customers whose plans haven't been
    migrated to entitlements yet.
    """
    from talk2record.usage.services import UsageTrackingService

    # No entitlement → resolver should fall back to features JSON.
    # The legacy resolver accepts ``"ai_usage_monthly_limit:<n>"`` strings
    # in a list, or ``{"ai_usage_monthly_limit": <n>}`` in a dict.
    subscription.plan.features = ["ai_usage_monthly_limit:750"]
    subscription.plan.save(update_fields=["features"])

    settings.AI_USAGE_MONTHLY_LIMIT_PER_ORG = 50
    assert UsageTrackingService.monthly_usage_limit(organization) == 750


@pytest.mark.django_db
def test_monthly_usage_limit_falls_back_to_settings_default(
    organization, settings,
):
    """No subscription, no entitlement → use the free-tier settings default."""
    from talk2record.usage.services import UsageTrackingService

    settings.AI_USAGE_MONTHLY_LIMIT_PER_ORG = 25
    assert UsageTrackingService.monthly_usage_limit(organization) == 25


@pytest.mark.django_db
def test_usage_summary_returns_populated_dataclass(
    organization, subscription, record,
):
    """``usage_summary`` should consolidate counter + limit + cycle bounds."""
    from talk2record.billing.models import PlanEntitlement
    from talk2record.usage.models import AIUsage
    from talk2record.usage.services import UsageTrackingService

    PlanEntitlement.objects.update_or_create(
        plan=subscription.plan,
        feature_key="ai.usage",
        defaults={"enabled": True, "limit": 100, "period": "monthly"},
    )
    # Two usage events in the current cycle (auto_now_add).
    AIUsage.objects.create(
        organization=organization,
        record=record,
        provider="openai",
        service_type=AIUsage.ServiceType.EXTRACTION,
        tokens_used=10,
    )
    AIUsage.objects.create(
        organization=organization,
        record=record,
        provider="openai",
        service_type=AIUsage.ServiceType.TRANSCRIPTION,
        tokens_used=20,
    )

    summary = UsageTrackingService.usage_summary(organization)

    assert summary.feature_key == "ai.usage"
    assert summary.used == 2
    assert summary.included == 100
    assert summary.percent_used == 2
    assert summary.plan_code == subscription.plan.code
    assert summary.billing_interval == subscription.billing_interval
    assert summary.subscription_status == subscription.status
    assert summary.period_start < summary.period_end


@pytest.mark.django_db
def test_billing_snapshot_surfaces_usage_block(workspace_user, subscription):
    """``GET /api/billing/`` should embed the usage block driven by Phase 2."""
    from talk2record.billing.models import PlanEntitlement

    PlanEntitlement.objects.update_or_create(
        plan=subscription.plan,
        feature_key="ai.usage",
        defaults={"enabled": True, "limit": 500, "period": "monthly"},
    )

    client = APIClient()
    client.force_authenticate(user=workspace_user)
    response = client.get(reverse("api:billing-list"))

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    sub = body["subscription"]
    assert sub["billingInterval"] == subscription.billing_interval
    assert sub["status"] == subscription.status
    assert sub["usage"]["featureKey"] == "ai.usage"
    assert sub["usage"]["included"] == 500
    assert sub["usage"]["used"] == 0
    assert "periodStart" in sub["usage"]
    assert "periodEnd" in sub["usage"]
