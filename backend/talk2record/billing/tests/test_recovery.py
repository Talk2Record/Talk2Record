"""Phase 5 — Billing Recovery System tests.

Covers:

- :class:`BillingRecoveryService.reset` Sync-Order semantics
  (version bump precedes Paddle, AIUsage current-cycle cleared, paid
  Transactions preserved, audit row captures before/after).
- DRF endpoint ``POST /api/admin/organizations/<id>/billing-reset/`` is
  guarded by ``IsPlatformStaff`` and runs the same service.
- Django admin reset actions render the reason-collection confirmation
  page and execute the reset on confirm.
- ``PaddleClient.update_transaction`` posts the right HTTP shape.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from http import HTTPStatus
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from talk2record.audit.models import AuditLog
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.billing.recovery_service import BillingRecoveryService
from talk2record.usage.models import AIUsage

# ---------------------------------------------------------------------------
# Fixtures local to Phase 5
# ---------------------------------------------------------------------------


@pytest.fixture
def staff_user(db, django_user_model):
    """Platform-staff user used for DRF endpoint tests."""
    return django_user_model.objects.create_user(
        email="staff@example.com",
        password="pw123456",
        name="Staff",
        is_staff=True,
    )


@pytest.fixture
def non_staff_user(db, django_user_model):
    return django_user_model.objects.create_user(
        email="someone@example.com",
        password="pw123456",
        name="Some User",
    )


@pytest.fixture
def usage_row(organization, record):
    """Create an AIUsage row inside the current billing cycle."""
    return AIUsage.objects.create(
        organization=organization,
        record=record,
        provider="openai",
        service_type=AIUsage.ServiceType.EXTRACTION,
        duration_seconds=10.0,
        tokens_used=200,
        cost_usd=Decimal("0.10"),
    )


@pytest.fixture
def patched_paddle_client():
    """Return a paddle service whose client looks unconfigured.

    Recovery service short-circuits paddle calls when ``client.is_configured()``
    is False, which is exactly what we want for tests that exercise local
    state mutations without touching the network.
    """
    service = MagicMock()
    service.client.is_configured.return_value = False
    return service


# ---------------------------------------------------------------------------
# BillingRecoveryService — 6-step contract
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_reset_bumps_billing_state_version_first(
    organization,
    subscription,
    usage_row,
    staff_user,
    patched_paddle_client,
):
    """The lock (version bump) must happen before any other mutation.

    We assert it by checking the FINAL version is exactly old + 1 and the
    sub is canceled — i.e. step 1 ran exactly once even though step 4
    also mutates the org's subscriptions.
    """
    original_version = organization.billing_state_version

    service = BillingRecoveryService(paddle=patched_paddle_client)
    report = service.reset(
        organization,
        actor=staff_user,
        reason="Disputed charge T-1234",
    )

    organization.refresh_from_db()
    subscription.refresh_from_db()

    assert organization.billing_state_version == original_version + 1
    assert report.new_billing_state_version == original_version + 1
    assert subscription.status == Subscription.Status.CANCELED
    assert subscription.canceled_at is not None


@pytest.mark.django_db
def test_reset_clears_current_cycle_usage_but_preserves_history(
    organization,
    subscription,
    record,
    staff_user,
    patched_paddle_client,
):
    """Step 4 should delete AIUsage rows in the current cycle ONLY.

    Older usage rows are part of the org's permanent record (audit /
    accounting) and must NOT be touched.
    """
    in_cycle = AIUsage.objects.create(
        organization=organization,
        record=record,
        provider="openai",
        service_type=AIUsage.ServiceType.EXTRACTION,
        tokens_used=100,
        cost_usd=Decimal("0.05"),
    )
    # Backdate one row to *before* the current cycle. We bypass auto_now_add
    # via an UPDATE so the row is preserved.
    history = AIUsage.objects.create(
        organization=organization,
        record=record,
        provider="openai",
        service_type=AIUsage.ServiceType.TRANSCRIPTION,
        tokens_used=50,
        cost_usd=Decimal("0.02"),
    )
    AIUsage.objects.filter(pk=history.pk).update(
        created_at=timezone.now() - timedelta(days=90),
    )

    report = BillingRecoveryService(paddle=patched_paddle_client).reset(
        organization,
        actor=staff_user,
        reason="Quota reset for dispute",
    )

    assert not AIUsage.objects.filter(pk=in_cycle.pk).exists()
    assert AIUsage.objects.filter(pk=history.pk).exists()
    assert report.usage_rows_cleared >= 1


@pytest.mark.django_db
def test_reset_preserves_paid_transactions(
    organization,
    subscription,
    staff_user,
    patched_paddle_client,
):
    """Paid Transactions are immutable financial records — never deleted."""
    # The `subscription` fixture already created one PAID Transaction (inv_1).
    paid_tx = Transaction.objects.get(
        subscription=subscription,
        status=Transaction.Status.PAID,
    )

    BillingRecoveryService(paddle=patched_paddle_client).reset(
        organization,
        actor=staff_user,
        reason="Sanity check",
    )

    assert Transaction.objects.filter(pk=paid_tx.pk).exists()
    paid_tx.refresh_from_db()
    assert paid_tx.status == Transaction.Status.PAID
    assert paid_tx.invoice_number == "inv_1"


@pytest.mark.django_db
def test_reset_writes_audit_row_with_old_and_new_state(
    organization,
    subscription,
    staff_user,
    patched_paddle_client,
):
    """The audit row must capture actor, reason, before/after snapshots."""
    BillingRecoveryService(paddle=patched_paddle_client).reset(
        organization,
        actor=staff_user,
        reason="Customer dispute Z-9001",
    )

    row = AuditLog.objects.filter(action="billing.reset").latest("created_at")
    assert row.resource_type == "organization"
    assert row.resource_id == str(organization.pk)
    assert row.actor_id == staff_user.pk
    assert row.organization_id == organization.pk
    assert row.metadata["reason"] == "Customer dispute Z-9001"
    assert "old_state" in row.metadata
    assert "new_state" in row.metadata
    # Before reset, sub was ACTIVE; after reset, it's CANCELED.
    old_states = {s["status"] for s in row.metadata["old_state"]["subscriptions"]}
    new_states = {s["status"] for s in row.metadata["new_state"]["subscriptions"]}
    assert Subscription.Status.ACTIVE in old_states
    assert new_states == {Subscription.Status.CANCELED}


@pytest.mark.django_db
def test_reset_requires_reason(
    organization,
    staff_user,
    patched_paddle_client,
):
    """Empty / whitespace reasons must be rejected — audit trail can't be empty."""
    with pytest.raises(ValueError):
        BillingRecoveryService(paddle=patched_paddle_client).reset(
            organization,
            actor=staff_user,
            reason="   ",
        )


@pytest.mark.django_db
def test_reset_optional_onboarding_reset_flag(
    organization,
    staff_user,
    patched_paddle_client,
):
    """``also_reset_onboarding=True`` clears profile_setup_completed only."""
    organization.profile_setup_completed = True
    organization.save(update_fields=["profile_setup_completed", "updated_at"])

    # Default: don't touch onboarding.
    BillingRecoveryService(paddle=patched_paddle_client).reset(
        organization,
        actor=staff_user,
        reason="Test",
    )
    organization.refresh_from_db()
    assert organization.profile_setup_completed is True

    # Explicit opt-in: clears the flag.
    BillingRecoveryService(paddle=patched_paddle_client).reset(
        organization,
        actor=staff_user,
        reason="Test 2",
        also_reset_onboarding=True,
    )
    organization.refresh_from_db()
    assert organization.profile_setup_completed is False


@pytest.mark.django_db
def test_reset_calls_paddle_cancel_when_client_configured(
    organization,
    subscription,
    staff_user,
):
    """When Paddle is configured, the service must call client.cancel and
    update_transaction for pending Transactions — but never delete anything.
    """
    # Add a PENDING transaction so the void path runs.
    Transaction.objects.create(
        subscription=subscription,
        provider_transaction_id="txn_pending_void",
        amount=Decimal("49.00"),
        currency="USD",
        status=Transaction.Status.PENDING,
        invoice_number="inv_pending",
        issued_at=timezone.now(),
    )

    fake_service = MagicMock()
    fake_service.client.is_configured.return_value = True
    fake_service.client.update_transaction.return_value = {}
    fake_service.cancel.return_value = None
    fake_service.sync_subscription.return_value = None

    BillingRecoveryService(paddle=fake_service).reset(
        organization,
        actor=staff_user,
        reason="Cancel test",
    )

    # Operational cancel of the active subscription.
    fake_service.cancel.assert_called_once()
    _cancel_args, cancel_kwargs = fake_service.cancel.call_args
    assert cancel_kwargs.get("effective_from") == "immediately"

    # Pending transaction was voided via PATCH /transactions/{id}.
    fake_service.client.update_transaction.assert_called_once()
    update_args = fake_service.client.update_transaction.call_args
    assert update_args.args[0] == "txn_pending_void"
    assert update_args.args[1] == {"status": "canceled"}


# ---------------------------------------------------------------------------
# DRF endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_billing_reset_endpoint_requires_platform_staff(
    organization,
    non_staff_user,
):
    client = APIClient()
    client.force_authenticate(user=non_staff_user)
    url = reverse("api:admin-organization-billing-reset", args=[organization.pk])

    response = client.post(url, {"reason": "anything"}, format="json")
    assert response.status_code in (HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED)


@pytest.mark.django_db
def test_billing_reset_endpoint_rejects_blank_reason(
    organization,
    staff_user,
):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    url = reverse("api:admin-organization-billing-reset", args=[organization.pk])

    response = client.post(url, {"reason": ""}, format="json")
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_billing_reset_endpoint_runs_service_for_staff(
    organization,
    subscription,
    staff_user,
):
    client = APIClient()
    client.force_authenticate(user=staff_user)
    url = reverse("api:admin-organization-billing-reset", args=[organization.pk])

    from talk2record.billing.recovery_service import BillingResetReport

    with patch(
        "talk2record.billing.admin_api.BillingRecoveryService",
    ) as service_cls:
        service_cls.return_value.reset.return_value = BillingResetReport(
            organization_id=organization.pk,
            actor_id=staff_user.pk,
            reason="Test dispute",
            old_state={},
            new_state={},
            paddle_subscription_ids=[],
            paddle_errors=[],
            usage_rows_cleared=0,
            onboarding_reset=False,
            new_billing_state_version=1,
        )
        response = client.post(
            url,
            {"reason": "Test dispute"},
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    payload = response.json()
    assert payload["new_billing_state_version"] == 1
    service_cls.return_value.reset.assert_called_once()


# ---------------------------------------------------------------------------
# Django admin per-org review + reset trigger
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_organization_review_renders_subscriptions_and_paddle_id(
    admin_client,
    organization,
    subscription,
):
    """The per-org review page lists subs + paddle customer id + reset trigger."""
    subscription.paddle_customer_id = "ctm_acme"
    subscription.save(update_fields=["paddle_customer_id"])

    response = admin_client.get(
        reverse("admin_billing_organization_review", args=[organization.pk]),
    )

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode("utf-8")
    assert organization.name in body
    assert subscription.plan.name in body
    assert "ctm_acme" in body
    assert "Reset billing" in body


@pytest.mark.django_db
def test_admin_reset_organization_view_requires_reason(
    admin_client,
    organization,
):
    """POSTing with blank reason should redirect back with an error message."""
    response = admin_client.post(
        reverse("admin_billing_reset_organization", args=[organization.pk]),
        data={"reason": ""},
    )
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse(
        "admin_billing_organization_review",
        args=[organization.pk],
    )


@pytest.mark.django_db
def test_admin_reset_organization_view_runs_service(
    admin_client,
    organization,
    subscription,
):
    """A POST with reason runs BillingRecoveryService and redirects."""
    with patch(
        "talk2record.billing.admin_views.BillingRecoveryService",
    ) as service_cls:
        service_cls.return_value.reset.return_value = MagicMock(
            paddle_errors=[],
            new_billing_state_version=1,
        )
        response = admin_client.post(
            reverse(
                "admin_billing_reset_organization",
                args=[organization.pk],
            ),
            data={"reason": "Refund issued"},
        )

    assert response.status_code == HTTPStatus.FOUND
    service_cls.return_value.reset.assert_called_once()
    # Reason / actor / org are passed through.
    call_kwargs = service_cls.return_value.reset.call_args.kwargs
    assert call_kwargs["reason"] == "Refund issued"


@pytest.mark.django_db
def test_admin_reset_organization_view_get_redirects(
    admin_client,
    organization,
):
    """GET is rejected (redirect to review page)."""
    response = admin_client.get(
        reverse("admin_billing_reset_organization", args=[organization.pk]),
    )
    assert response.status_code == HTTPStatus.FOUND


# ---------------------------------------------------------------------------
# PaddleClient.update_transaction shape
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_paddle_client_update_transaction_uses_patch(monkeypatch):
    """``update_transaction`` must PATCH /transactions/{id} with the payload."""
    from talk2record.billing.paddle_client import PaddleClient

    client = PaddleClient()
    fake_request = MagicMock(return_value={"data": {"id": "txn_1"}})
    monkeypatch.setattr(client, "request", fake_request)

    result = client.update_transaction("txn_1", {"status": "canceled"})

    assert result == {"data": {"id": "txn_1"}}
    fake_request.assert_called_once_with(
        "PATCH",
        "/transactions/txn_1",
        json={"status": "canceled"},
    )
