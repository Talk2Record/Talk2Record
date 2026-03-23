from __future__ import annotations

from celery import shared_task
from django.contrib.auth import get_user_model

from talk2record.audit.services import AuditService
from talk2record.events.decorators import already_handled
from talk2record.organizations.models import Organization


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_audit(self, event_payload: dict) -> None:  # noqa: ARG001
    if already_handled(event_payload, "audit"):
        return

    user = None
    user_id = event_payload.get("user_id")
    if user_id is not None:
        user = get_user_model().objects.filter(pk=user_id).first()

    organization = None
    organization_id = event_payload.get("organization_id")
    if organization_id is not None:
        organization = Organization.objects.filter(pk=organization_id).first()

    AuditService.log(
        action=str(event_payload.get("name", "event.unknown")),
        resource_type=str(event_payload.get("resource_type", "domain_event")),
        resource_id=str(event_payload.get("resource_id", "")),
        actor=user,
        organization=organization,
        metadata=dict(event_payload.get("metadata") or {}),
    )
