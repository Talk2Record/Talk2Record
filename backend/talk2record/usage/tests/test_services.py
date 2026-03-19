from __future__ import annotations

import pytest

from talk2record.usage.models import AIUsage
from talk2record.usage.services import UsageTrackingService


@pytest.mark.django_db
def test_log_ai_usage_creates_row(record):
    usage = UsageTrackingService.log_ai_usage(
        record=record,
        provider="mock",
        service_type=AIUsage.ServiceType.TRANSCRIPTION,
        duration_seconds=0.5,
    )

    assert usage.organization_id == record.organization_id
    assert usage.record_id == record.id
    assert usage.service_type == AIUsage.ServiceType.TRANSCRIPTION
