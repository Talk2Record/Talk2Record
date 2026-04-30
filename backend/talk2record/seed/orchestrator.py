from __future__ import annotations

from django.db import transaction

from talk2record.seed.builders import SeedOptions
from talk2record.seed.builders import SeedSummary
from talk2record.seed.reference_data import sync_reference_data


class SeedDataOrchestrator:
    """Run the platform/admin seed.

    The seed only provisions reference data (legal documents, integration
    singletons, plans/prices/entitlements). Tenant data is never created.
    """

    def __init__(self, *, options: SeedOptions | None = None) -> None:
        self.options = options or SeedOptions()

    def run(self) -> SeedSummary:
        summary = SeedSummary()
        with transaction.atomic():
            sync_reference_data(summary)
        return summary
