from __future__ import annotations

from django.db import transaction

from talk2record.seed.builders import SeedOptions
from talk2record.seed.builders import SeedSummary
from talk2record.seed.builders import SeedWorkspaceBuilder
from talk2record.seed.reference_data import sync_reference_data
from talk2record.seed.time_range import SeedTimeRange


class SeedDataOrchestrator:
    def __init__(self, *, options: SeedOptions) -> None:
        self.options = options

    def run(self) -> SeedSummary:
        summary = SeedSummary()
        time_range = SeedTimeRange.from_lookback(
            days=self.options.days,
            months=self.options.months,
            years=self.options.years,
        )
        with transaction.atomic():
            reference_data = sync_reference_data(summary)
        builder = SeedWorkspaceBuilder(
            options=self.options,
            reference_data=reference_data,
            time_range=time_range,
            summary=summary,
        )
        for index in range(1, self.options.organization_count + 1):
            builder.build_workspace(index)
        return summary
