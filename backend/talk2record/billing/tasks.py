from __future__ import annotations

import logging

from celery import shared_task

from talk2record.events.decorators import already_handled
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_billing(self, event_payload: dict) -> None:  # noqa: ARG001
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
        message = str(metadata.get("message") or "Your last payment attempt failed. Please update your payment method.")
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
        message = str(metadata.get("message") or "Your subscription has been successfully activated.")
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
def process_paddle_webhook(self, event_pk: int) -> str:  # noqa: ARG001
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
def sync_paddle_state(self) -> dict[str, int]:  # noqa: ARG001
    """Re-pull every subscription's live state from Paddle.

    Triggered by the ``/admin/billing/sync-all/`` button and (optionally) by
    a daily Celery beat schedule. Per the two-plane model, this is a
    *read* against Paddle: we never mutate Paddle here, only refresh the
    Django mirror to recover from missed/late webhooks.

    The task is rate-limited (10/min via Celery) and per-subscription errors
    are logged but never abort the loop — Paddle API hiccups on one org must
    not block sync for the rest.

    Returns a small summary dict so the admin can see numbers in task logs.
    """
    # Local import: keeps Paddle/Django import graph quiet at module import
    # time (this task is only enqueued from staff actions).
    from talk2record.billing.models import Subscription
    from talk2record.billing.paddle_client import PaddleAPIError
    from talk2record.billing.paddle_service import PaddleBillingService

    service = PaddleBillingService()
    if not service.client.is_configured():
        logger.warning("sync_paddle_state skipped: Paddle client not configured")
        return {"synced": 0, "failed": 0, "skipped": 0}

    queryset = Subscription.objects.exclude(provider_subscription_id="").only(
        "id",
        "provider_subscription_id",
        "status",
        "paddle_customer_id",
    )

    synced = 0
    failed = 0
    for sub in queryset.iterator(chunk_size=50):
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
        except Exception:  # noqa: BLE001 — keep the loop alive
            failed += 1
            logger.exception(
                "sync_paddle_state: unexpected error for %s",
                sub.provider_subscription_id,
            )
    logger.info(
        "sync_paddle_state finished: synced=%s failed=%s", synced, failed,
    )
    return {"synced": synced, "failed": failed, "skipped": 0}
