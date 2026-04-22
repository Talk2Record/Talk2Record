from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from django.db import transaction

from talk2record.events.names import AI_EXTRACTION_COMPLETED
from talk2record.events.names import AI_EXTRACTION_FAILED
from talk2record.events.names import AI_EXTRACTION_STARTED
from talk2record.events.names import AI_TRANSCRIPTION_COMPLETED
from talk2record.events.names import AI_TRANSCRIPTION_FAILED
from talk2record.events.names import AI_TRANSCRIPTION_STARTED
from talk2record.events.names import BILLING_LIMIT_EXCEEDED
from talk2record.events.names import BILLING_PAYMENT_FAILED
from talk2record.events.names import BILLING_SUBSCRIPTION_CREATED
from talk2record.events.names import INGESTION_FAILED
from talk2record.events.names import INGESTION_RECEIVED
from talk2record.events.names import INGESTION_VALIDATED
from talk2record.events.names import LEGAL_ACCEPTED
from talk2record.events.names import LEGAL_ATTESTED
from talk2record.events.names import MEMBERSHIP_ACCEPTED
from talk2record.events.names import MEMBERSHIP_INVITED
from talk2record.events.names import MEMBERSHIP_REMOVED
from talk2record.events.names import MEMBERSHIP_REVOKED
from talk2record.events.names import MEMBERSHIP_ROLE_CHANGED
from talk2record.events.names import RECORD_CREATED
from talk2record.events.names import RECORD_PROCESSING_COMPLETED
from talk2record.events.names import RECORD_PROCESSING_FAILED
from talk2record.events.names import RECORD_PROCESSING_STARTED
from talk2record.events.names import RECORD_STORED
from talk2record.events.names import RECORD_UPDATED
from talk2record.events.names import SYSTEM_ERROR
from talk2record.events.names import USAGE_AI_INCREMENTED
from talk2record.events.names import USER_IMPERSONATED
from talk2record.events.names import USER_PROFILE_UPDATED
from talk2record.events.names import USER_REACTIVATED
from talk2record.events.names import USER_REGISTERED
from talk2record.events.names import USER_SUSPENDED
from talk2record.events.names import VOICE_NOTE_RECEIVED
from talk2record.events.names import WHATSAPP_MESSAGE_DELIVERED
from talk2record.events.names import WHATSAPP_MESSAGE_FAILED
from talk2record.events.names import WHATSAPP_MESSAGE_READ
from talk2record.events.names import WHATSAPP_MESSAGE_RECEIVED
from talk2record.events.names import WHATSAPP_MESSAGE_SENT
from talk2record.events.names import WHATSAPP_STATUS_UPDATED
from talk2record.events.types import DomainEvent

_AUDIT = "talk2record.audit.tasks.handle_domain_event_for_audit"
_ANALYTICS = "talk2record.analytics.tasks.handle_domain_event_for_analytics"
_NOTIFICATIONS = "talk2record.notifications.tasks.handle_domain_event_for_notifications"
_USAGE = "talk2record.usage.tasks.handle_domain_event_for_usage"
_BILLING = "talk2record.billing.tasks.handle_domain_event_for_billing"


class EventBus:
    _handlers: dict[str, list[str]] = defaultdict(list)
    _bootstrapped = False

    @classmethod
    def register(cls, event_name: str, task_name: str) -> None:
        handlers = cls._handlers.setdefault(event_name, [])
        if task_name not in handlers:
            handlers.append(task_name)

    @classmethod
    def get_handlers(cls, event_name: str) -> list[str]:
        cls._bootstrap()
        return list(cls._handlers.get(event_name, []))

    @classmethod
    def publish(cls, event: DomainEvent) -> None:
        cls._bootstrap()
        from talk2record.events.models import DomainEvent as DomainEventRecord
        from talk2record.events.tasks import dispatch_domain_event

        DomainEventRecord.objects.create(
            id=event.event_id,
            name=event.name,
            organization_id=event.organization_id,
            user_id=event.user_id,
            resource_type=event.resource_type or "",
            resource_id=event.resource_id or "",
            payload=event.to_payload(),
            occurred_at=event.occurred_at,
        )
        dispatch_domain_event.delay(event.to_payload())

    @classmethod
    def _bootstrap(cls) -> None:
        if cls._bootstrapped:
            return
        register_defaults(cls.register)
        cls._bootstrapped = True


def register_defaults(register: Callable[[str, str], None]) -> None:
    # Ingestion
    register(INGESTION_RECEIVED, _AUDIT)
    register(INGESTION_VALIDATED, _AUDIT)
    register(INGESTION_FAILED, _AUDIT)

    # Record lifecycle
    register(RECORD_CREATED, _AUDIT)
    register(RECORD_CREATED, _ANALYTICS)
    register(RECORD_UPDATED, _AUDIT)
    register(RECORD_STORED, _AUDIT)
    register(RECORD_STORED, _ANALYTICS)
    register(RECORD_STORED, _NOTIFICATIONS)

    # Record processing lifecycle
    register(RECORD_PROCESSING_STARTED, _AUDIT)
    register(RECORD_PROCESSING_STARTED, _ANALYTICS)
    register(RECORD_PROCESSING_COMPLETED, _AUDIT)
    register(RECORD_PROCESSING_COMPLETED, _ANALYTICS)
    register(RECORD_PROCESSING_FAILED, _AUDIT)
    register(RECORD_PROCESSING_FAILED, _ANALYTICS)

    # AI transcription lifecycle
    register(AI_TRANSCRIPTION_STARTED, _AUDIT)
    register(AI_TRANSCRIPTION_COMPLETED, _AUDIT)
    register(AI_TRANSCRIPTION_COMPLETED, _USAGE)
    register(AI_TRANSCRIPTION_FAILED, _AUDIT)

    # AI extraction lifecycle
    register(AI_EXTRACTION_STARTED, _AUDIT)
    register(AI_EXTRACTION_COMPLETED, _AUDIT)
    register(AI_EXTRACTION_COMPLETED, _USAGE)
    register(AI_EXTRACTION_FAILED, _AUDIT)

    # Usage / billing
    register(USAGE_AI_INCREMENTED, _ANALYTICS)
    register(BILLING_LIMIT_EXCEEDED, _AUDIT)
    register(BILLING_LIMIT_EXCEEDED, _BILLING)
    register(BILLING_PAYMENT_FAILED, _AUDIT)
    register(BILLING_PAYMENT_FAILED, _BILLING)
    register(BILLING_SUBSCRIPTION_CREATED, _AUDIT)
    register(BILLING_SUBSCRIPTION_CREATED, _ANALYTICS)

    # Legal
    register(LEGAL_ACCEPTED, _AUDIT)
    register(LEGAL_ACCEPTED, _ANALYTICS)
    register(LEGAL_ATTESTED, _AUDIT)
    register(LEGAL_ATTESTED, _ANALYTICS)

    # Users / system
    register(USER_REGISTERED, _AUDIT)
    register(USER_SUSPENDED, _AUDIT)
    register(USER_REACTIVATED, _AUDIT)
    register(USER_IMPERSONATED, _AUDIT)
    register(USER_PROFILE_UPDATED, _AUDIT)
    register(SYSTEM_ERROR, _AUDIT)

    # WhatsApp public contract — audit the full lifecycle. Consumers like
    # ingestion/records subscribe to ``voice_note.received`` via @on handlers
    # registered in their own apps rather than here.
    register(WHATSAPP_MESSAGE_RECEIVED, _AUDIT)
    register(WHATSAPP_MESSAGE_SENT, _AUDIT)
    register(WHATSAPP_MESSAGE_DELIVERED, _AUDIT)
    register(WHATSAPP_MESSAGE_READ, _AUDIT)
    register(WHATSAPP_MESSAGE_FAILED, _AUDIT)
    register(WHATSAPP_MESSAGE_FAILED, _NOTIFICATIONS)
    register(WHATSAPP_STATUS_UPDATED, _AUDIT)
    register(VOICE_NOTE_RECEIVED, _AUDIT)

    # Memberships
    register(MEMBERSHIP_INVITED, _AUDIT)
    register(MEMBERSHIP_INVITED, _NOTIFICATIONS)
    register(MEMBERSHIP_ACCEPTED, _AUDIT)
    register(MEMBERSHIP_ACCEPTED, _NOTIFICATIONS)
    register(MEMBERSHIP_ACCEPTED, _ANALYTICS)
    register(MEMBERSHIP_REVOKED, _AUDIT)
    register(MEMBERSHIP_REMOVED, _AUDIT)
    register(MEMBERSHIP_ROLE_CHANGED, _AUDIT)


def publish_after_commit(event: DomainEvent) -> None:
    transaction.on_commit(lambda: EventBus.publish(event))
