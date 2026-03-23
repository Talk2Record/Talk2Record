from __future__ import annotations

from celery import shared_task

from talk2record.events.decorators import already_handled
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization


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
