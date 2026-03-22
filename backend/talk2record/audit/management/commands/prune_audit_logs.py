from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from talk2record.audit.models import AuditLog
from talk2record.audit.services import AuditService


class Command(BaseCommand):
    help = (
        "Prune old organization.api_key.used audit events. "
        "Lifecycle events (created, rotated, revoked) are never pruned."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--days",
            type=int,
            default=None,
            help="Retention in days (default: AUDIT_API_KEY_USED_RETENTION_DAYS)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report count without deleting",
        )

    def handle(self, *args, **options) -> None:
        retention_days = options["days"]
        if retention_days is None:
            retention_days = getattr(
                settings,
                "AUDIT_API_KEY_USED_RETENTION_DAYS",
                90,
            )
        if retention_days <= 0:
            self.stdout.write(
                self.style.WARNING(
                    "Retention days is 0 or negative; skipping prune.",
                ),
            )
            return

        cutoff = timezone.now() - timezone.timedelta(days=retention_days)
        qs = AuditLog.objects.filter(
            action=AuditService.ACTION_API_KEY_USED,
            resource_type=AuditService.RESOURCE_TYPE_API_KEY,
            created_at__lt=cutoff,
        )
        count = qs.count()

        if count == 0:
            self.stdout.write("No audit logs to prune.")
            return

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING(
                    f"Would delete {count} organization.api_key.used events "
                    f"older than {cutoff.date()} (dry run)",
                ),
            )
            return

        deleted, _ = qs.delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Pruned {deleted} organization.api_key.used events "
                f"older than {retention_days} days.",
            ),
        )
