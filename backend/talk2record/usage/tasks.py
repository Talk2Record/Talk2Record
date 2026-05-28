from __future__ import annotations

from decimal import Decimal

from celery import shared_task

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.decorators import already_handled
from talk2record.events.names import AI_EXTRACTION_COMPLETED
from talk2record.events.names import AI_TRANSCRIPTION_COMPLETED
from talk2record.events.names import USAGE_AI_INCREMENTED
from talk2record.records.models import Record
from talk2record.usage.services import UsageTrackingService


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_usage(self, event_payload: dict) -> None:
    if already_handled(event_payload, "usage"):
        return

    event_name = str(event_payload.get("name", ""))
    if event_name not in {AI_TRANSCRIPTION_COMPLETED, AI_EXTRACTION_COMPLETED}:
        return

    record_id = event_payload.get("resource_id")
    if not record_id:
        return
    record = Record.objects.filter(pk=record_id).first()
    if record is None:
        return

    metadata = dict(event_payload.get("metadata") or {})
    ai_usage = UsageTrackingService.log_ai_usage(
        record=record,
        provider=str(metadata.get("provider", "unknown")),
        service_type=str(metadata.get("service_type", "transcription")),
        duration_seconds=float(metadata.get("duration_seconds", 0) or 0),
        tokens_used=int(metadata.get("tokens_used", 0) or 0),
        cost_usd=Decimal(str(metadata.get("cost_usd", "0.00"))),
    )

    publish_after_commit(
        DomainEvent(
            name=USAGE_AI_INCREMENTED,
            organization_id=record.organization_id,
            user_id=record.created_by_id,
            resource_type="ai_usage",
            resource_id=str(ai_usage.pk),
            metadata={
                "service_type": ai_usage.service_type,
                "provider": ai_usage.provider,
                "record_id": str(record.pk),
            },
        ),
    )
