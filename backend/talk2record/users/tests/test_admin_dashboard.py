from __future__ import annotations

import json
from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import RequestFactory
from django.utils import timezone

from talk2record.billing.models import Plan
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.users.admin_dashboard import dashboard_callback
from talk2record.users.tests.factories import UserFactory


def _call(url: str) -> dict:
    factory = RequestFactory()
    request = factory.get(url)
    request.user = UserFactory.build(is_staff=True)
    return dashboard_callback(request, {})


@pytest.mark.django_db
class TestDashboardCallbackShape:
    def test_returns_expected_context_keys(self):
        ctx = _call("/admin/")
        assert "onboarding_report" in ctx
        assert "onboarding_groups" in ctx
        assert "onboarding_percent" in ctx
        assert "kpi_cards" in ctx
        assert "filters" in ctx
        assert "range_choices" in ctx
        assert "source_choices" in ctx
        assert "available_organizations" in ctx
        assert "records_per_day_json" in ctx
        assert "records_by_status_json" in ctx
        assert "revenue_per_month_json" in ctx

    def test_chart_json_is_valid(self):
        ctx = _call("/admin/")
        for key in (
            "records_per_day_json",
            "records_by_status_json",
            "revenue_per_month_json",
            "top_organizations_json",
            "provider_mix_json",
        ):
            parsed = json.loads(ctx[key])
            assert isinstance(parsed, list)

    def test_kpi_cards_have_title_and_metric(self):
        ctx = _call("/admin/")
        for card in ctx["kpi_cards"]:
            assert "title" in card
            assert "metric" in card

    def test_default_filters_applied(self):
        ctx = _call("/admin/")
        assert ctx["filters"]["range"] == "30d"
        assert ctx["filters"]["organization"] == ""
        assert ctx["filters"]["source"] == ""


@pytest.mark.django_db
class TestFilters:
    def test_invalid_range_falls_back_to_default(self):
        ctx = _call("/admin/?range=banana")
        assert ctx["filters"]["range"] == "30d"

    def test_invalid_source_is_ignored(self):
        ctx = _call("/admin/?source=not-a-source")
        assert ctx["filters"]["source"] == ""

    def test_all_time_range_includes_old_records(self, organization, workspace_user):
        old = Record.objects.create(
            organization=organization,
            created_by=workspace_user,
            source=Record.Source.WHATSAPP,
            type=Record.Type.VOICE_NOTE,
            audio_url="https://example.com/a.ogg",
        )
        Record.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(days=365),
        )

        window_ctx = _call("/admin/?range=7d")
        all_ctx = _call("/admin/?range=all")

        def _records_metric(ctx):
            for card in ctx["kpi_cards"]:
                if str(card["title"]) == "Records processed":
                    return card["metric"]
            return 0

        assert _records_metric(window_ctx) == 0
        assert _records_metric(all_ctx) == 1

    def test_organization_filter_scopes_kpis(self, workspace_user):
        org_a = Organization.objects.create(name="Alpha", slug="alpha")
        org_b = Organization.objects.create(name="Beta", slug="beta")
        Membership.objects.create(
            user=workspace_user,
            organization=org_a,
            role=Membership.Role.OWNER,
            status=Membership.Status.ACTIVE,
        )
        Record.objects.create(
            organization=org_a,
            created_by=workspace_user,
            source=Record.Source.WHATSAPP,
            type=Record.Type.VOICE_NOTE,
            audio_url="https://example.com/x.ogg",
        )
        Record.objects.create(
            organization=org_b,
            created_by=workspace_user,
            source=Record.Source.UPLOAD,
            type=Record.Type.VOICE_NOTE,
            audio_url="https://example.com/y.ogg",
        )

        ctx = _call(f"/admin/?organization={org_a.pk}")

        def _records_metric(ctx):
            for card in ctx["kpi_cards"]:
                if str(card["title"]) == "Records processed":
                    return card["metric"]
            return 0

        assert _records_metric(ctx) == 1
        assert ctx["filters"]["organization"] == str(org_a.pk)

    def test_source_filter_narrows_records(self, organization, workspace_user):
        Record.objects.create(
            organization=organization,
            created_by=workspace_user,
            source=Record.Source.WHATSAPP,
            type=Record.Type.VOICE_NOTE,
            audio_url="https://example.com/w.ogg",
        )
        Record.objects.create(
            organization=organization,
            created_by=workspace_user,
            source=Record.Source.UPLOAD,
            type=Record.Type.VOICE_NOTE,
            audio_url="https://example.com/u.ogg",
        )
        ctx = _call("/admin/?source=whatsapp&range=all")

        def _records_metric(ctx):
            for card in ctx["kpi_cards"]:
                if str(card["title"]) == "Records processed":
                    return card["metric"]
            return 0

        assert _records_metric(ctx) == 1


@pytest.mark.django_db
class TestRevenueRollup:
    def test_revenue_sum_from_paid_transactions(self, organization):
        plan = Plan.objects.create(
            code="starter", name="Starter", base_price=Decimal("9.00"),
        )
        subscription = Subscription.objects.create(
            organization=organization,
            plan=plan,
            status=Subscription.Status.ACTIVE,
            currency="USD",
            amount=Decimal("9.00"),
            seats=1,
            current_period_end=timezone.now() + timedelta(days=30),
        )
        Transaction.objects.create(
            subscription=subscription,
            provider_transaction_id="tx1",
            amount=Decimal("9.00"),
            currency="USD",
            status=Transaction.Status.PAID,
            invoice_number="inv1",
            issued_at=timezone.now(),
            paid_at=timezone.now(),
        )
        Transaction.objects.create(
            subscription=subscription,
            provider_transaction_id="tx2",
            amount=Decimal("50.00"),
            currency="USD",
            status=Transaction.Status.PENDING,
            invoice_number="inv2",
            issued_at=timezone.now(),
            paid_at=None,
        )

        ctx = _call("/admin/?range=all")
        revenue_cards = [c for c in ctx["kpi_cards"] if str(c["title"]) == "Revenue captured"]
        assert revenue_cards, "missing revenue card"
        assert "9.00" in revenue_cards[0]["metric"]


@pytest.mark.django_db
class TestOnboardingIntegration:
    def test_onboarding_progress_reflected_in_kpi(self):
        ctx = _call("/admin/")
        onboarding_card = next(
            card for card in ctx["kpi_cards"]
            if str(card["title"]) == "Onboarding progress"
        )
        assert "/" in onboarding_card["metric"]
        assert ctx["onboarding_total"] > 0
        assert ctx["onboarding_percent"] == ctx["onboarding_report"].percent
