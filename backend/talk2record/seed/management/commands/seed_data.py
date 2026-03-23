from __future__ import annotations

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.test.utils import override_settings

from talk2record.seed.builders import SeedOptions
from talk2record.seed.constants import DEFAULT_DAYS
from talk2record.seed.constants import DEFAULT_ORGANIZATION_COUNT
from talk2record.seed.constants import DEFAULT_PASSWORD
from talk2record.seed.constants import DEFAULT_RECORDS_PER_DAY
from talk2record.seed.constants import DEFAULT_USERS_PER_ORGANIZATION
from talk2record.seed.orchestrator import SeedDataOrchestrator


class Command(BaseCommand):
    help = "Generate idempotent demo seed data for the full Talk2Record application."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--days", type=int, default=DEFAULT_DAYS)
        parser.add_argument("--months", type=int, default=0)
        parser.add_argument("--years", type=int, default=0)
        parser.add_argument("--orgs", type=int, default=DEFAULT_ORGANIZATION_COUNT)
        parser.add_argument(
            "--users-per-org",
            type=int,
            default=DEFAULT_USERS_PER_ORGANIZATION,
        )
        parser.add_argument(
            "--records-per-day",
            type=int,
            default=DEFAULT_RECORDS_PER_DAY,
        )
        parser.add_argument("--password", default=DEFAULT_PASSWORD)

    def handle(self, *args, **options) -> None:
        integer_options = (
            options["days"],
            options["months"],
            options["years"],
            options["orgs"],
            options["users_per_org"],
            options["records_per_day"],
        )
        if any(value < 0 for value in integer_options):
            message = "Seed arguments must be zero or greater."
            raise CommandError(message)
        if options["orgs"] == 0:
            message = "At least one organization must be seeded."
            raise CommandError(message)
        if options["users_per_org"] == 0:
            message = "At least one user per organization is required."
            raise CommandError(message)
        if options["records_per_day"] == 0:
            message = "At least one record per day is required."
            raise CommandError(message)

        seed_options = SeedOptions(
            days=options["days"],
            months=options["months"],
            years=options["years"],
            organization_count=options["orgs"],
            users_per_organization=options["users_per_org"],
            records_per_day=options["records_per_day"],
            password=options["password"],
        )
        with override_settings(CELERY_TASK_ALWAYS_EAGER=True):
            summary = SeedDataOrchestrator(options=seed_options).run()

        self.stdout.write(self.style.SUCCESS("Seed data generation complete."))
        for bucket, created, updated in summary.rows():
            self.stdout.write(f"- {bucket}: created={created}, updated={updated}")
