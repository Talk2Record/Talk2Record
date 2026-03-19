from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from talk2record.usage.models import AIUsage

if TYPE_CHECKING:
    from talk2record.records.models import Record


class UsageTrackingService:
    @staticmethod
    def log_ai_usage(  # noqa: PLR0913
        *,
        record: Record,
        provider: str,
        service_type: str,
        duration_seconds: float = 0,
        tokens_used: int = 0,
        cost_usd: Decimal = Decimal("0.00"),
    ) -> AIUsage:
        return AIUsage.objects.create(
            organization=record.organization,
            record=record,
            provider=provider,
            service_type=service_type,
            duration_seconds=duration_seconds,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )
