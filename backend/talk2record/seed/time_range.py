from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import time
from datetime import timedelta

from django.utils import timezone


def _shift_months(value: datetime, months: int) -> datetime:
    month_index = (value.year * 12 + value.month - 1) + months
    year, month = divmod(month_index, 12)
    month += 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@dataclass(frozen=True, slots=True)
class SeedTimeRange:
    start_at: datetime
    end_at: datetime

    @classmethod
    def from_lookback(
        cls,
        *,
        days: int = 0,
        months: int = 0,
        years: int = 0,
        end_at: datetime | None = None,
    ) -> SeedTimeRange:
        effective_end = end_at or timezone.now()
        start_at = _shift_months(
            effective_end,
            -(months + years * 12),
        ) - timedelta(days=days)
        return cls(start_at=start_at, end_at=effective_end)

    @property
    def total_days(self) -> int:
        return (self.end_at.date() - self.start_at.date()).days + 1

    def iter_dates(self) -> list[date]:
        start_date = self.start_at.date()
        return [
            start_date + timedelta(days=offset) for offset in range(self.total_days)
        ]

    def at_slot(self, value: date, *, slot: int, total_slots: int) -> datetime:
        base_hour = 9
        interval = max(1, 8 // max(total_slots, 1))
        hour = min(23, base_hour + (slot * interval))
        minute = (slot * 17) % 60
        naive_datetime = datetime.combine(value, time(hour=hour, minute=minute))
        current_timezone = timezone.get_current_timezone()
        return timezone.make_aware(naive_datetime, current_timezone)
