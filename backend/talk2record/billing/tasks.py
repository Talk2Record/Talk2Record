from __future__ import annotations

import logging

from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

from talk2record.events.decorators import already_handled
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)
PADDLE_SYNC_SUMMARY_CACHE_KEY = "billing:paddle_sync:last_summary"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_billing(self, event_payload: dict) -> None:
    if already_handled(event_payload, "billing"):
        return

    event_name = str(event_payload.get("name", ""))
    if event_name not in {BILLING_PAYMENT_FAILED, BILLING_SUBSCRIPTION_CREATED}:
        return

    organization_id = event_payload.get("organization_id")
    organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        return

    event_id = str(event_payload.get("event_id", ""))
    metadata = dict(event_payload.get("metadata") or {})
    memberships = organization.memberships.filter(
        status=Membership.Status.ACTIVE,
    ).select_related("user")

    if event_name == BILLING_PAYMENT_FAILED:
        title = "Payment failed"
        message = str(
            metadata.get("message")
            or "Your last payment attempt failed. Please update your payment method.",
        )
        for membership in memberships:
            NotificationService.create(
                user=membership.user,
                notification_type=Notification.Type.BILLING_PAYMENT,
                title=title,
                message=message,
                organization=organization,
                metadata={"event_id": event_id},
            )

    elif event_name == BILLING_SUBSCRIPTION_CREATED:
        title = "Subscription activated"
        message = str(
            metadata.get("message")
            or "Your subscription has been successfully activated.",
        )
        for membership in memberships:
            NotificationService.create(
                user=membership.user,
                notification_type=Notification.Type.BILLING_SUBSCRIPTION,
                title=title,
                message=message,
                organization=organization,
                metadata={"event_id": event_id},
            )


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def process_paddle_webhook(self, event_pk: int) -> str:
    """Apply a previously-persisted ``PaddleWebhookEvent`` row asynchronously.

    Only invoked when ``settings.PADDLE_WEBHOOK_ASYNC`` is truthy
    (default: off). The synchronous HTTP path inserts the event row + does
    the idempotency check, then enqueues this task; the task is the only
    place that mutates ``Subscription`` / ``Transaction`` in async mode.

    The reset-race version guard inside ``webhook_pipeline.replay_event``
    still applies, so a billing reset that happens between enqueue and
    worker pickup will correctly mark the event SKIPPED.
    """
    from talk2record.billing.models import PaddleWebhookEvent
    from talk2record.billing.webhook_pipeline import replay_event

    event = PaddleWebhookEvent.objects.filter(pk=event_pk).first()
    if event is None:
        logger.warning("process_paddle_webhook: event pk=%s not found", event_pk)
        return "missing"
    # Don't re-run an event we already accepted — re-queues from a redelivered
    # task should be a no-op.
    if event.status not in {
        PaddleWebhookEvent.Status.RECEIVED,
        PaddleWebhookEvent.Status.FAILED,
    }:
        return event.status
    result = replay_event(event)
    return result.status


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
    rate_limit="10/m",
)
def sync_paddle_state(self) -> dict[str, int]:  # noqa: C901, PLR0915
    """Sync local billing state with Paddle (push catalog, then pull subs).

    Triggered by the ``/admin/billing/sync-all/`` button and (optionally) by
    a daily Celery beat schedule.

    Phase order:
    1) Push active local ``Plan`` + ``PlanPrice`` rows to Paddle so newly seeded
       catalog entries get Paddle product/price ids.
    2) Pull each subscription's live status from Paddle into Django to recover
       from missed/late webhooks.

    The task is rate-limited (10/min via Celery) and per-subscription errors
    are logged but never abort the loop — Paddle API hiccups on one org must
    not block sync for the rest.

    Returns a small summary dict so the admin can see numbers in task logs.
    """
    # Local import: keeps Paddle/Django import graph quiet at module import
    # time (this task is only enqueued from staff actions).
    from talk2record.billing.models import Plan
    from talk2record.billing.models import PlanPrice
    from talk2record.billing.models import Subscription
    from talk2record.billing.paddle_client import PaddleAPIError
    from talk2record.billing.paddle_service import PaddleBillingService

    service = PaddleBillingService()
    cache.set(
        PADDLE_SYNC_SUMMARY_CACHE_KEY,
        {
            "status": "running",
            "started_at": timezone.now().isoformat(),
            "task_id": getattr(self.request, "id", ""),
        },
        timeout=7 * 24 * 60 * 60,
    )
    if not service.client.is_configured():
        logger.warning("sync_paddle_state skipped: Paddle client not configured")
        result = {
            "status": "skipped",
            "plans_pushed": 0,
            "prices_pushed": 0,
            "entitlements_published": 0,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "finished_at": timezone.now().isoformat(),
            "task_id": getattr(self.request, "id", ""),
        }
        cache.set(PADDLE_SYNC_SUMMARY_CACHE_KEY, result, timeout=7 * 24 * 60 * 60)
        return result

    plans_queryset = (
        Plan.objects.filter(is_active=True)
        .prefetch_related("entitlements")
        .only(
            "id",
            "code",
            "name",
            "paddle_product_id",
            "updated_at",
        )
    )
    prices_queryset = (
        PlanPrice.objects.filter(active=True)
        .select_related("plan")
        .only(
            "id",
            "plan_id",
            "interval",
            "amount",
            "currency",
            "billing_cycle",
            "trial_period",
            "paddle_price_id",
            "active",
            "updated_at",
        )
    )
    subs_queryset = Subscription.objects.exclude(provider_subscription_id="").only(
        "id",
        "provider_subscription_id",
        "status",
        "paddle_customer_id",
    )

    plans_pushed = 0
    prices_pushed = 0
    entitlements_published = 0
    synced = 0
    failed = 0

    for plan in plans_queryset.iterator(chunk_size=50):
        try:
            service.push_plan(plan)
            plans_pushed += 1
            entitlements_published += sum(
                1 for ent in plan.entitlements.all() if ent.enabled
            )
        except PaddleAPIError as exc:
            failed += 1
            logger.warning(
                "sync_paddle_state: plan %s push failed (%s)",
                plan.code,
                exc,
            )
        except Exception:
            failed += 1
            logger.exception(
                "sync_paddle_state: unexpected plan push error for %s",
                plan.code,
            )

    for price in prices_queryset.iterator(chunk_size=100):
        try:
            service.push_price(price)
            prices_pushed += 1
        except PaddleAPIError as exc:
            failed += 1
            logger.warning(
                "sync_paddle_state: price %s/%s push failed (%s)",
                price.plan.code,
                price.interval,
                exc,
            )
        except Exception:
            failed += 1
            logger.exception(
                "sync_paddle_state: unexpected price push error for %s/%s",
                price.plan.code,
                price.interval,
            )

    for sub in subs_queryset.iterator(chunk_size=50):
        try:
            service.sync_subscription(sub)
            synced += 1
        except PaddleAPIError as exc:
            failed += 1
            logger.warning(
                "sync_paddle_state: %s failed (%s)",
                sub.provider_subscription_id,
                exc,
            )
        except Exception:
            failed += 1
            logger.exception(
                "sync_paddle_state: unexpected error for %s",
                sub.provider_subscription_id,
            )
    logger.info(
        "sync_paddle_state finished: plans_pushed=%s prices_pushed=%s "
        "entitlements_published=%s synced=%s failed=%s",
        plans_pushed,
        prices_pushed,
        entitlements_published,
        synced,
        failed,
    )
    result = {
        "status": "finished",
        "plans_pushed": plans_pushed,
        "prices_pushed": prices_pushed,
        "entitlements_published": entitlements_published,
        "synced": synced,
        "failed": failed,
        "skipped": 0,
        "finished_at": timezone.now().isoformat(),
        "task_id": getattr(self.request, "id", ""),
    }
    cache.set(PADDLE_SYNC_SUMMARY_CACHE_KEY, result, timeout=7 * 24 * 60 * 60)
    return result
