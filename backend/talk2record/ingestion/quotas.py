from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.utils import timezone

from talk2record.records.models import Record

if TYPE_CHECKING:
    from talk2record.organizations.models import Organization


class IngestionQuotaService:
    @staticmethod
    def can_ingest_whatsapp(organization: Organization) -> bool:
        daily_limit = int(getattr(settings, "INGESTION_DAILY_RECORD_LIMIT_PER_ORG", 0))
        if daily_limit <= 0:
            return True

        now = timezone.now()
        start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
        todays_count = Record.objects.filter(
            organization=organization,
            source=Record.Source.WHATSAPP,
            created_at__gte=start_of_day,
        ).count()
        return todays_count < daily_limit
