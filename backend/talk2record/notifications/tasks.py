from __future__ import annotations

from celery import shared_task

from talk2record.events.decorators import already_handled
from talk2record.events.names import RECORD_STORED
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
def handle_domain_event_for_notifications(self, event_payload: dict) -> None:  # noqa: ARG001
    if already_handled(event_payload, "notifications"):
        return

    event_id = str(event_payload.get("event_id", ""))
    event_name = str(event_payload.get("name", ""))
    if event_name != RECORD_STORED:
        return

    organization_id = event_payload.get("organization_id")
    organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        return

    metadata = dict(event_payload.get("metadata") or {})
    title = str(metadata.get("title") or "Record processed")
    message = str(metadata.get("message") or "")
    link_url = str(metadata.get("link_url") or "/dashboard/records")
    resource_id = event_payload.get("resource_id")

    memberships = organization.memberships.filter(
        status=Membership.Status.ACTIVE,
    ).select_related("user")
    for membership in memberships:
        NotificationService.create(
            user=membership.user,
            notification_type=Notification.Type.RECORD_STORED,
            title=title,
            message=message,
            link_url=link_url,
            organization=organization,
            metadata={"record_id": resource_id, "event_id": event_id},
        )
