from __future__ import annotations

from celery import shared_task
from django.utils import timezone

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.services import AnalyticsService
from talk2record.events.decorators import already_handled
from talk2record.events.names import LEGAL_ACCEPTED
from talk2record.events.names import LEGAL_ATTESTED
from talk2record.events.names import RECORD_STORED
from talk2record.organizations.models import Organization


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_analytics(self, event_payload: dict) -> None:  # noqa: ARG001
    if already_handled(event_payload, "analytics"):
        return

    event_name = str(event_payload.get("name", ""))
    organization_id = event_payload.get("organization_id")
    organization = Organization.objects.filter(pk=organization_id).first()

    if event_name == RECORD_STORED and organization is not None:
        metric_date = timezone.now().date()
        daily_metric, _ = DailyMetric.objects.get_or_create(
            organization=organization,
            metric_date=metric_date,
        )
        daily_metric.records_created += 1
        daily_metric.voice_processed += 1
        daily_metric.save(update_fields=["records_created", "voice_processed"])

    if event_name in {RECORD_STORED, LEGAL_ACCEPTED, LEGAL_ATTESTED}:
        AnalyticsService.track_event(
            name=event_name.replace(".", "_"),
            category=event_name.split(".", maxsplit=1)[0],
            organization=organization,
            properties=dict(event_payload.get("metadata") or {}),
        )
