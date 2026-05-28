from http import HTTPStatus
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Subscription
from talk2record.billing.tasks import handle_domain_event_for_billing
from talk2record.core.vault import SecretVault
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.notifications.models import Notification
from talk2record.organizations.models import Organization


@pytest.mark.django_db
def test_plan_subscription_and_transaction_str(plan, subscription):
    transaction = subscription.transactions.get()

    assert str(plan) == "Growth (USD)"
    assert (
        str(subscription)
        == f"{subscription.organization.name}: {subscription.plan.name}"
    )
    assert str(transaction) == "inv_1"


@pytest.mark.django_db
def test_billing_admin_pages(admin_client, subscription):
    urls = [
        reverse("admin:billing_plan_changelist"),
        reverse("admin:billing_subscription_changelist"),
        reverse("admin:billing_transaction_changelist"),
        reverse("admin:billing_paddlesettings_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_paddle_settings_singleton_persists_environment_and_secrets():
    settings = PaddleSettings.get_solo()
    settings.environment = PaddleSettings.Environment.PRODUCTION
    settings.encrypted_api_key = SecretVault.encrypt("pdl_live_secret")
    settings.save(
        update_fields=["environment", "encrypted_api_key", "updated_at"],
    )

    from talk2record.billing.paddle_client import PaddleClient

    client = PaddleClient()
    assert client.base_url() == PaddleClient.PRODUCTION_BASE_URL
    assert client.api_key() == "pdl_live_secret"


@pytest.mark.django_db
def test_paddle_settings_environment_toggle_changes_base_url():
    settings = PaddleSettings.get_solo()
    settings.environment = PaddleSettings.Environment.SANDBOX
    settings.encrypted_api_key = SecretVault.encrypt("pdl_sandbox")
    settings.save(
        update_fields=["environment", "encrypted_api_key", "updated_at"],
    )

    from talk2record.billing.paddle_client import PaddleClient

    client = PaddleClient()
    assert client.base_url() == PaddleClient.SANDBOX_BASE_URL

    settings.environment = PaddleSettings.Environment.PRODUCTION
    settings.save(update_fields=["environment", "updated_at"])

    assert client.base_url() == PaddleClient.PRODUCTION_BASE_URL


@pytest.mark.django_db
def test_handle_domain_event_for_billing_payment_failed_creates_notifications(
    workspace_user,
    organization,
):
    event_payload = {
        "event_id": "billing-test-uuid-001",
        "name": BILLING_PAYMENT_FAILED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {"provider": "paddle"},
    }

    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_PAYMENT,
    ).exists()


@pytest.mark.django_db
def test_handle_domain_event_for_billing_subscription_created_creates_notifications(
    workspace_user,
    organization,
):
    event_payload = {
        "event_id": "billing-test-uuid-002",
        "name": BILLING_SUBSCRIPTION_CREATED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {"provider": "paddle"},
    }

    handle_domain_event_for_billing(event_payload)

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.BILLING_SUBSCRIPTION,
    ).exists()


@pytest.mark.django_db
def test_handle_domain_event_for_billing_is_idempotent(workspace_user, organization):
    event_payload = {
        "event_id": "billing-test-uuid-003",
        "name": BILLING_PAYMENT_FAILED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "billing_webhook",
        "resource_id": "paddle",
        "metadata": {},
    }

    handle_domain_event_for_billing(event_payload)
    handle_domain_event_for_billing(event_payload)

    assert (
        Notification.objects.filter(
            organization=organization,
            type=Notification.Type.BILLING_PAYMENT,
            metadata__event_id="billing-test-uuid-003",
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_billing_webhook_view_emits_payment_failed_event(settings, subscription):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    published: list[str] = []

    payload = {
        "event_id": "evt_failed_1",
        "event_type": "transaction.payment_failed",
        "data": {
            "id": "txn_failed_1",
            "subscription_id": subscription.provider_subscription_id,
            "currency_code": "USD",
            "details": {"totals": {"grand_total": "4900"}},
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    with patch("talk2record.billing.webhook_pipeline.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_PAYMENT_FAILED in published


@pytest.mark.django_db(transaction=True)
def test_billing_webhook_view_emits_subscription_created_event(settings, subscription):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    published: list[str] = []

    payload = {
        "event_id": "evt_created_xyz",
        "event_type": "subscription.created",
        "data": {
            "id": "sub_xyz",
            "status": "active",
            "items": [],
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    with patch("talk2record.billing.webhook_pipeline.EventBus.publish") as mock_publish:
        mock_publish.side_effect = lambda event: published.append(event.name)
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert BILLING_SUBSCRIPTION_CREATED in published


@pytest.mark.django_db
def test_plans_catalog_is_public(client):
    from talk2record.billing.models import Plan
    from talk2record.seed.constants import PLAN_DEFINITIONS

    for definition in PLAN_DEFINITIONS:
        Plan.objects.update_or_create(
            code=definition["code"],
            defaults={
                "name": definition["name"],
                "base_price": definition["base_price"],
                "currency": definition["currency"],
                "region": definition.get("region", ""),
                "features": list(definition.get("features", [])),
                "is_active": True,
            },
        )

    response = client.get(reverse("api:billing-plans"))
    assert response.status_code == HTTPStatus.OK
    codes = {row["code"] for row in response.json()}
    assert "starter" in codes
    assert "growth" in codes
    assert "scale" in codes
    growth = next(row for row in response.json() if row["code"] == "growth")
    assert growth["monthly_amount"] is not None
    assert "entitlements" in growth


@pytest.mark.django_db
def test_change_plan_updates_subscription(workspace_user, subscription, plan):
    from decimal import Decimal

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
    PlanPrice.objects.update_or_create(
        plan=starter,
        interval="month",
        currency="USD",
        defaults={
            "amount": Decimal("19.00"),
            "active": True,
            "paddle_price_id": "pri_starter",
        },
    )
    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={
            "amount": Decimal("49.00"),
            "active": True,
            "paddle_price_id": "pri_growth",
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
            {"plan": "starter", "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    assert response.json()["status"] == "updated"
    mock_service.change_plan.assert_called_once()


@pytest.mark.django_db
def test_change_plan_same_plan_returns_400(workspace_user, subscription):
    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True

        response = client.post(
            reverse("api:billing-change-plan"),
            {"plan": subscription.plan.code, "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.django_db
def test_change_plan_without_subscription_returns_checkout(
    workspace_user,
    organization,
    plan,
):
    from talk2record.billing.models import PlanPrice

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={
            "amount": plan.base_price,
            "active": True,
            "paddle_price_id": "pri_growth",
        },
    )

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    with patch("talk2record.billing.views.PaddleBillingService") as mock_service_cls:
        mock_service = mock_service_cls.return_value
        mock_service.client.is_configured.return_value = True
        mock_service.create_checkout.return_value = type(
            "S",
            (),
            {
                "status": "created",
                "checkout_url": "http://localhost:3000/checkout?_ptxn=txn_test",
                "transaction_id": "txn_test",
            },
        )()

        response = client.post(
            reverse("api:billing-change-plan"),
            {"plan": plan.code, "acceptedBillingTerms": True},
            format="json",
        )

    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["status"] == "checkout_required"
    assert body["checkoutUrl"].startswith("http://")
    assert body["transactionId"] == "txn_test"


@pytest.mark.django_db
def test_create_checkout_does_not_send_success_url_as_checkout_url(organization, plan):
    from talk2record.billing.models import PlanPrice
    from talk2record.billing.paddle_service import PaddleBillingService

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={
            "amount": plan.base_price,
            "active": True,
            "paddle_price_id": "pri_growth",
        },
    )

    service = PaddleBillingService()
    captured: dict = {}

    def fake_create_transaction(payload):
        captured["payload"] = payload
        return {
            "data": {
                "id": "txn_abc",
                "checkout": {"url": "http://localhost:3000/checkout?_ptxn=txn_abc"},
            },
        }

    service.client.create_transaction = fake_create_transaction  # type: ignore[method-assign]
    service.client._settings = type(  # type: ignore[method-assign]
        "S",
        (),
        {
            "default_success_url": "",
            "default_payment_link": "http://localhost:3000/checkout",
        },
    )

    session = service.create_checkout(
        organization=organization,
        plan=plan,
        success_url="http://localhost:3000/onboarding?checkout=success",
    )

    payload = captured["payload"]
    assert payload["checkout"]["url"] == "http://localhost:3000/checkout"
    assert (
        payload["custom_data"]["success_url"]
        == "http://localhost:3000/onboarding?checkout=success"
    )
    assert session.transaction_id == "txn_abc"
    assert session.checkout_url.endswith("?_ptxn=txn_abc")


@pytest.mark.django_db
def test_paddle_config_requires_client_side_token(workspace_user):
    settings = PaddleSettings.get_solo()
    settings.client_side_token = ""
    settings.save(update_fields=["client_side_token", "updated_at"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    response = client.get(reverse("api:billing-paddle-config"))
    assert response.status_code == HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.django_db
def test_paddle_config_returns_token(workspace_user):
    settings = PaddleSettings.get_solo()
    settings.client_side_token = "test_example_token"
    settings.environment = PaddleSettings.Environment.SANDBOX
    settings.save(update_fields=["client_side_token", "environment", "updated_at"])

    client = APIClient()
    client.force_authenticate(user=workspace_user)

    response = client.get(reverse("api:billing-paddle-config"))
    assert response.status_code == HTTPStatus.OK
    body = response.json()
    assert body["clientSideToken"] == "test_example_token"
    assert body["environment"] == "sandbox"


@pytest.mark.django_db
def test_plans_catalog_includes_trial_period(client):
    from talk2record.billing.models import Plan
    from talk2record.billing.models import PlanPrice
    from talk2record.seed.constants import PLAN_DEFINITIONS

    for definition in PLAN_DEFINITIONS:
        plan, _ = Plan.objects.update_or_create(
            code=definition["code"],
            defaults={
                "name": definition["name"],
                "base_price": definition["base_price"],
                "currency": definition["currency"],
                "region": definition.get("region", ""),
                "features": list(definition.get("features", [])),
                "is_active": True,
            },
        )
        for price in definition.get("prices", ()):
            PlanPrice.objects.update_or_create(
                plan=plan,
                interval=price["interval"],
                currency=price["currency"],
                defaults={
                    "amount": price["amount"],
                    "billing_cycle": dict(price.get("billing_cycle") or {}),
                    "trial_period": dict(price.get("trial_period") or {}),
                    "active": True,
                },
            )

    response = client.get(reverse("api:billing-plans"))
    assert response.status_code == HTTPStatus.OK
    starter = next(row for row in response.json() if row["code"] == "starter")
    monthly = next(price for price in starter["prices"] if price["interval"] == "month")
    assert monthly["trialPeriod"] == {"interval": "day", "frequency": 14}
    scale = next(row for row in response.json() if row["code"] == "scale")
    scale_monthly = next(
        price for price in scale["prices"] if price["interval"] == "month"
    )
    assert scale_monthly["trialPeriod"] is None


@pytest.mark.django_db
def test_trial_checkout_sets_automatic_collection_and_trial_custom_data(
    organization,
    plan,
):
    """A checkout against a price that carries a trial_period should:

    - send ``collection_mode=automatic`` so Paddle stores the card and bills $0 now
    - tag ``custom_data.trial=true`` (+ interval/frequency) so support /
      analytics can distinguish trial activations from paid checkouts.
    """
    from decimal import Decimal

    from talk2record.billing.models import PlanPrice
    from talk2record.billing.paddle_service import PaddleBillingService

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={
            "amount": Decimal("49.00"),
            "active": True,
            "paddle_price_id": "pri_growth_trial",
            "trial_period": {"interval": "day", "frequency": 14},
        },
    )

    service = PaddleBillingService()
    captured: dict = {}

    def fake_create_transaction(payload):
        captured["payload"] = payload
        return {
            "data": {
                "id": "txn_trial",
                "checkout": {"url": "http://x/?_ptxn=txn_trial"},
            },
        }

    service.client.create_transaction = fake_create_transaction  # type: ignore[method-assign]
    service.client._settings = type(  # type: ignore[method-assign]
        "S",
        (),
        {"default_success_url": "", "default_payment_link": "http://x/"},
    )

    service.create_checkout(organization=organization, plan=plan, interval="month")

    payload = captured["payload"]
    assert payload["collection_mode"] == "automatic"
    assert payload["custom_data"]["trial"] == "true"
    assert payload["custom_data"]["trial_interval"] == "day"
    assert payload["custom_data"]["trial_frequency"] == "14"


@pytest.mark.django_db
def test_non_trial_checkout_omits_trial_custom_data(organization, plan):
    """When the resolved price has no trial_period, custom_data must not be tagged."""
    from decimal import Decimal

    from talk2record.billing.models import PlanPrice
    from talk2record.billing.paddle_service import PaddleBillingService

    PlanPrice.objects.update_or_create(
        plan=plan,
        interval="month",
        currency="USD",
        defaults={
            "amount": Decimal("49.00"),
            "active": True,
            "paddle_price_id": "pri_growth_no_trial",
            "trial_period": {},
        },
    )

    service = PaddleBillingService()
    captured: dict = {}

    def fake_create_transaction(payload):
        captured["payload"] = payload
        return {
            "data": {"id": "txn_paid", "checkout": {"url": "http://x/?_ptxn=txn_paid"}},
        }

    service.client.create_transaction = fake_create_transaction  # type: ignore[method-assign]
    service.client._settings = type(  # type: ignore[method-assign]
        "S",
        (),
        {"default_success_url": "", "default_payment_link": "http://x/"},
    )

    service.create_checkout(organization=organization, plan=plan, interval="month")

    custom_data = captured["payload"]["custom_data"]
    # collection_mode is always automatic now; that's fine.
    assert captured["payload"]["collection_mode"] == "automatic"
    assert "trial" not in custom_data
    assert "trial_interval" not in custom_data
    assert "trial_frequency" not in custom_data


@pytest.mark.django_db(transaction=True)
def test_subscription_created_webhook_stamps_period_end_for_trialing(
    settings,
    subscription,
):
    """``subscription.created`` with ``status=trialing`` must persist
    ``current_period_end`` so the serializer can expose ``trial_ends_at``.
    """
    from talk2record.billing.models import Subscription

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    trial_end_iso = "2030-01-15T00:00:00Z"

    payload = {
        "event_id": "evt_trial_started_1",
        "event_type": "subscription.created",
        "data": {
            "id": subscription.provider_subscription_id,
            "status": "trialing",
            "items": [],
            "current_billing_period": {
                "starts_at": "2030-01-01T00:00:00Z",
                "ends_at": trial_end_iso,
            },
            "next_billed_at": trial_end_iso,
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    response = client.post(reverse("api-billing-webhook"), data=payload, format="json")
    assert response.status_code == 202

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.TRIALING
    assert subscription.current_period_end is not None
    assert subscription.current_period_end.isoformat().startswith("2030-01-15")


@pytest.mark.django_db
def test_admin_billing_dashboard_renders_with_kpis(admin_client, subscription):
    """Smoke-test the new /admin/billing/dashboard/ page.

    Verifies it returns 200, includes the expected KPI titles, and surfaces
    the seeded subscription's plan in the distribution table.
    """
    response = admin_client.get(reverse("admin_billing_dashboard"))

    assert response.status_code == HTTPStatus.OK
    body = response.content.decode("utf-8")
    # KPI titles
    assert "Monthly Recurring Revenue" in body
    assert "Annual Run Rate" in body
    assert "Active subscriptions" in body
    assert "Trialing" in body
    assert "Past-due" in body
    assert "Failed payments" in body
    assert "Revenue this month" in body
    assert "Voluntary churn" in body
    # Plan distribution surfaces the seeded subscription's plan
    assert subscription.plan.name in body
    # Recent transactions table picks up the fixture invoice
    assert "inv_1" in body


@pytest.mark.django_db
def test_admin_billing_dashboard_computes_mrr_from_intervals(
    admin_client,
    organization,
    plan,
):
    """A monthly + annual sub on the same org should produce MRR = month + year/12."""
    from decimal import Decimal

    from talk2record.billing.models import Subscription

    Subscription.objects.create(
        organization=organization,
        plan=plan,
        provider_subscription_id="sub_monthly",
        status=Subscription.Status.ACTIVE,
        currency="USD",
        amount=Decimal("49.00"),
        billing_interval="month",
        seats=1,
    )
    Subscription.objects.create(
        organization=organization,
        plan=plan,
        provider_subscription_id="sub_annual",
        status=Subscription.Status.ACTIVE,
        currency="USD",
        amount=Decimal("588.00"),  # = 49 × 12
        billing_interval="year",
        seats=1,
    )

    response = admin_client.get(reverse("admin_billing_dashboard"))
    assert response.status_code == HTTPStatus.OK
    body = response.content.decode("utf-8")
    # MRR = 49 (monthly) + 588/12 = 49 + 49 = 98.00
    assert "$98.00" in body
    # ARR = 98 * 12 = 1,176.00 (formatted with thousands separator)
    assert "$1,176.00" in body


@pytest.mark.django_db
def test_admin_billing_sync_all_enqueues_task(admin_client, subscription):
    """POST /admin/billing/sync-all/ enqueues sync_paddle_state and redirects."""
    with patch("talk2record.billing.tasks.sync_paddle_state.delay") as mock_delay:
        response = admin_client.post(reverse("admin_billing_sync_all"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("admin_billing_dashboard")
    mock_delay.assert_called_once_with()


@pytest.mark.django_db
def test_admin_billing_sync_all_get_redirects_to_dashboard(admin_client):
    """GET is rejected (redirect) — only POST should enqueue."""
    response = admin_client.get(reverse("admin_billing_sync_all"))
    assert response.status_code == HTTPStatus.FOUND
    assert response.url == reverse("admin_billing_dashboard")


@pytest.mark.django_db
def test_sync_paddle_state_task_short_circuits_when_unconfigured():
    """The Celery task should noop (not raise) when Paddle is not configured."""
    from talk2record.billing.tasks import sync_paddle_state

    with patch(
        "talk2record.billing.paddle_service.PaddleBillingService",
    ) as mock_service_cls:
        mock_service_cls.return_value.client.is_configured.return_value = False
        result = sync_paddle_state.apply().get()

    assert result == {
        "plans_pushed": 0,
        "prices_pushed": 0,
        "entitlements_published": 0,
        "synced": 0,
        "failed": 0,
        "skipped": 0,
    }


# ---------------------------------------------------------------------------
# Phase 4.5 — Webhook hardening: idempotency + reset-race + out-of-order
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_webhook_duplicate_event_id_is_processed_exactly_once(
    settings,
    subscription,
):
    """Replaying the same Paddle event must not duplicate mutations.

    The unique constraint on ``PaddleWebhookEvent.paddle_event_id`` is the
    natural idempotency key. Second delivery should be marked DUPLICATE
    and the local Subscription's billing_interval mustn't be touched
    a second time.
    """
    from talk2record.billing.models import PaddleWebhookEvent

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    payload = {
        "event_id": "evt_duplicate_replay_1",
        "event_type": "subscription.canceled",
        "data": {
            "id": subscription.provider_subscription_id,
            "canceled_at": "2030-03-01T00:00:00Z",
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    r1 = client.post(reverse("api-billing-webhook"), data=payload, format="json")
    r2 = client.post(reverse("api-billing-webhook"), data=payload, format="json")

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r1.json()["status"] == "accepted"
    assert r2.json()["status"] == "duplicate"

    # Exactly one PaddleWebhookEvent row for this event_id
    assert (
        PaddleWebhookEvent.objects.filter(
            paddle_event_id="evt_duplicate_replay_1",
        ).count()
        == 1
    )


@pytest.mark.django_db(transaction=True)
def test_webhook_skipped_when_billing_state_version_changes_during_dispatch(
    settings,
    subscription,
):
    """Reset-race guard: a webhook that arrives concurrently with a billing
    reset must be discarded if ``billing_state_version`` bumped during
    dispatch.

    We simulate the race by monkey-patching ``dispatch_event`` to bump the
    org's version *before* it returns — modelling a reset committing in
    parallel. The mutation must roll back and the event row must record
    status=SKIPPED.
    """
    from django.db.models import F

    from talk2record.billing.models import PaddleWebhookEvent
    from talk2record.billing.models import Subscription
    from talk2record.organizations.models import Organization

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    payload = {
        "event_id": "evt_race_1",
        "event_type": "subscription.canceled",
        "data": {
            "id": subscription.provider_subscription_id,
            "canceled_at": "2030-04-01T00:00:00Z",
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    original_status = subscription.status

    def _race(event_type, event_data, org_id):
        # Apply the mutation first (will get rolled back), then bump the
        # version to simulate a reset finishing between snapshot and commit.
        Subscription.objects.filter(
            provider_subscription_id=event_data.get("id"),
        ).update(status=Subscription.Status.CANCELED)
        Organization.objects.filter(pk=subscription.organization_id).update(
            billing_state_version=F("billing_state_version") + 1,
        )

    with patch(
        "talk2record.billing.webhook_pipeline.dispatch_event",
        side_effect=_race,
    ):
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert response.json()["status"] == "skipped"

    # Mutation rolled back — local sub is unchanged
    subscription.refresh_from_db()
    assert subscription.status == original_status

    # Event row records the skip + reason
    row = PaddleWebhookEvent.objects.get(paddle_event_id="evt_race_1")
    assert row.status == PaddleWebhookEvent.Status.SKIPPED
    assert "billing_state_version" in row.error


@pytest.mark.django_db(transaction=True)
def test_webhook_out_of_order_updated_after_canceled_does_not_reactivate(
    settings,
    subscription,
):
    """If ``subscription.updated`` arrives *after* ``subscription.canceled``
    (out-of-order delivery from Paddle), the local CANCELED state must NOT
    be flipped back to active.

    Only the explicit reactivation events (``subscription.activated`` /
    ``subscription.resumed``) are allowed to reopen a canceled sub.
    """
    from talk2record.billing.models import Subscription

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    sub_id = subscription.provider_subscription_id
    org_id = str(subscription.organization_id)

    # 1. Cancel
    cancel_payload = {
        "event_id": "evt_order_cancel",
        "event_type": "subscription.canceled",
        "data": {
            "id": sub_id,
            "canceled_at": "2030-05-01T00:00:00Z",
            "custom_data": {"organization_id": org_id},
        },
    }
    r1 = client.post(reverse("api-billing-webhook"), data=cancel_payload, format="json")
    assert r1.status_code == 202
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.CANCELED

    # 2. A late subscription.updated arrives with status=active (stale state)
    update_payload = {
        "event_id": "evt_order_update_stale",
        "event_type": "subscription.updated",
        "data": {
            "id": sub_id,
            "status": "active",
            "items": [],
            "custom_data": {"organization_id": org_id},
        },
    }
    r2 = client.post(reverse("api-billing-webhook"), data=update_payload, format="json")
    assert r2.status_code == 202
    # Webhook is still recorded as accepted (the table is append-only audit),
    # but the local sub MUST remain canceled.
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.CANCELED


@pytest.mark.django_db(transaction=True)
def test_webhook_resumed_can_reactivate_canceled_sub(settings, subscription):
    """The explicit ``subscription.resumed`` event IS allowed to revive a
    canceled sub. This is the legitimate "subscribe again" path that must
    bypass the out-of-order guard from the previous test.
    """
    from talk2record.billing.models import Subscription

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    sub_id = subscription.provider_subscription_id
    org_id = str(subscription.organization_id)

    # Pre-cancel via the model so we only exercise the resume path here.
    Subscription.objects.filter(pk=subscription.pk).update(
        status=Subscription.Status.CANCELED,
    )

    resume_payload = {
        "event_id": "evt_resume_real",
        "event_type": "subscription.resumed",
        "data": {
            "id": sub_id,
            "status": "active",
            "items": [],
            "custom_data": {"organization_id": org_id},
        },
    }
    response = client.post(
        reverse("api-billing-webhook"),
        data=resume_payload,
        format="json",
    )
    assert response.status_code == 202
    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.ACTIVE


@pytest.mark.django_db(transaction=True)
def test_webhook_missing_event_id_is_ignored_with_202(settings, subscription):
    """Malformed payloads without ``event_id`` should be silently ignored.

    We *never* 4xx Paddle for malformed payloads — that triggers retry
    storms. Instead we audit and return 202 so Paddle stops sending.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    payload = {
        "event_type": "subscription.created",
        # missing event_id on purpose
        "data": {
            "id": subscription.provider_subscription_id,
            "status": "active",
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }
    response = client.post(reverse("api-billing-webhook"), data=payload, format="json")
    assert response.status_code == 202
    assert response.json()["status"] == "ignored"


@pytest.mark.django_db(transaction=True)
def test_webhook_stale_organization_id_returns_202_not_500(settings, plan):
    """Paddle replays with a deleted ``organization_id`` must not 500.

    Common after a local DB reset: checkout stamped ``custom_data`` with
    org pk=3, volumes were wiped, Paddle still delivers
    ``subscription.created`` for that id. We ACK with 202 and skip the
    upsert instead of violating the subscription FK.
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    stale_org_id = 999_999
    assert not Organization.objects.filter(pk=stale_org_id).exists()

    payload = {
        "event_id": "evt_stale_org_1",
        "event_type": "subscription.created",
        "data": {
            "id": "sub_stale_org_test",
            "status": "active",
            "items": [],
            "custom_data": {"organization_id": str(stale_org_id)},
        },
    }

    with patch("talk2record.billing.webhook_pipeline.EventBus.publish") as mock_publish:
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert response.json()["status"] in {"accepted", "failed"}
    mock_publish.assert_not_called()
    assert not Subscription.objects.filter(
        provider_subscription_id="sub_stale_org_test",
    ).exists()


@pytest.mark.django_db(transaction=True)
def test_webhook_async_path_enqueues_celery_task(settings, subscription):
    """When PADDLE_WEBHOOK_ASYNC=True the view returns 202+queued and the
    actual dispatch happens in the Celery worker (and the row gets
    inserted up-front for idempotency).
    """
    from talk2record.billing.models import PaddleWebhookEvent

    settings.PADDLE_WEBHOOK_ASYNC = True
    settings.CELERY_TASK_ALWAYS_EAGER = False  # we don't want eager execution here

    client = APIClient()
    payload = {
        "event_id": "evt_async_1",
        "event_type": "subscription.canceled",
        "data": {
            "id": subscription.provider_subscription_id,
            "canceled_at": "2030-06-01T00:00:00Z",
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    with patch("talk2record.billing.tasks.process_paddle_webhook.delay") as mock_delay:
        response = client.post(
            reverse("api-billing-webhook"),
            data=payload,
            format="json",
        )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    # Idempotency row already exists pre-dispatch
    row = PaddleWebhookEvent.objects.get(paddle_event_id="evt_async_1")
    assert row.status == PaddleWebhookEvent.Status.RECEIVED
    mock_delay.assert_called_once_with(row.pk)


@pytest.mark.django_db(transaction=True)
def test_subscription_canceled_webhook_stamps_canceled_at(settings, subscription):
    """``subscription.canceled`` must record ``canceled_at`` (from payload or now)."""
    from talk2record.billing.models import Subscription

    settings.CELERY_TASK_ALWAYS_EAGER = True
    client = APIClient()
    cancel_iso = "2030-02-01T12:34:56Z"

    payload = {
        "event_id": "evt_canceled_1",
        "event_type": "subscription.canceled",
        "data": {
            "id": subscription.provider_subscription_id,
            "canceled_at": cancel_iso,
            "custom_data": {"organization_id": str(subscription.organization_id)},
        },
    }

    response = client.post(reverse("api-billing-webhook"), data=payload, format="json")
    assert response.status_code == 202

    subscription.refresh_from_db()
    assert subscription.status == Subscription.Status.CANCELED
    assert subscription.canceled_at is not None
    assert subscription.canceled_at.isoformat().startswith("2030-02-01")
