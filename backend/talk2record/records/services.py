from __future__ import annotations

from decimal import Decimal

from talk2record.analytics.services import AnalyticsService
from talk2record.audit.services import AuditService
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership
from talk2record.records.models import Record


class RecordProcessingService:
    @staticmethod
    def transcribe(record: Record) -> Record:
        if not record.voice_transcript:
            record.voice_transcript = (
                f"Structured transcript placeholder for {record.customer_name} "
                f"and {record.product}."
            )
        record.status = Record.Status.TRANSCRIBED
        record.save(update_fields=["voice_transcript", "status", "updated_at"])
        return record

    @staticmethod
    def extract_structured_data(record: Record) -> Record:
        if not record.amount:
            record.amount = Decimal("0.00")
        if not record.confidence_score:
            record.confidence_score = Decimal("0.950")
        record.status = Record.Status.REVIEW
        record.save(update_fields=["amount", "confidence_score", "status", "updated_at"])
        return record

    @staticmethod
    def store(record: Record) -> Record:
        record.status = Record.Status.STORED
        record.save(update_fields=["status", "updated_at"])
        AuditService.log(
            action="record.stored",
            resource_type="record",
            resource_id=str(record.pk),
            actor=record.created_by,
            organization=record.organization,
            metadata={"source": record.source},
        )
        AnalyticsService.track_event(
            name="record_stored",
            category="records",
            organization=record.organization,
            properties={"source": record.source, "status": record.status},
        )

        title = f"Voice note from {record.customer_name} has been processed"
        message = f"Record: {record.product} - {record.quantity} x {record.currency} {record.amount}"
        link_url = f"/dashboard/records"
        for membership in record.organization.memberships.filter(status=Membership.Status.ACTIVE):
            NotificationService.create(
                user=membership.user,
                notification_type=Notification.Type.RECORD_STORED,
                title=title,
                message=message,
                link_url=link_url,
                organization=record.organization,
                metadata={"record_id": record.pk},
            )

        return record
