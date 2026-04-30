from __future__ import annotations

from django.core.management.base import BaseCommand

from talk2record.seed.builders import SeedOptions
from talk2record.seed.orchestrator import SeedDataOrchestrator


class Command(BaseCommand):
    help = (
        "Provision platform/admin reference data: legal document versions, "
        "integration singletons (WhatsApp, Paddle, AI), and the default "
        "billing plans, prices and entitlements. Idempotent — safe to run "
        "multiple times. Tenant data (organizations, users, records, "
        "subscriptions, transactions) is never created or modified."
    )

    def add_arguments(self, parser) -> None:  # noqa: ARG002 - reserved for future toggles
        return None

    def handle(self, *args, **options) -> None:  # noqa: ARG002
        summary = SeedDataOrchestrator(options=SeedOptions()).run()

        self.stdout.write(
            self.style.SUCCESS("Platform seed data provisioned."),
        )
        rows = summary.rows()
        if not rows:
            self.stdout.write("All seed records already up to date.")
            return
        for bucket, created, updated in rows:
            self.stdout.write(f"- {bucket}: created={created}, updated={updated}")
