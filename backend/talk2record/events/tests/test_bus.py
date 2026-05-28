from __future__ import annotations

import pytest

from talk2record.events.bus import EventBus
from talk2record.events.bus import publish_after_commit
from talk2record.events.bus import register_defaults
from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import LEGAL_ACCEPTED
from talk2record.events.names import RECORD_STORED
from talk2record.events.types import DomainEvent


@pytest.fixture(autouse=True)
def _reset_event_bus():
    """Reset EventBus state between tests."""
    original_handlers = dict(EventBus._handlers)
    original_bootstrapped = EventBus._bootstrapped
    EventBus._handlers.clear()
    EventBus._bootstrapped = False
    yield
    EventBus._handlers.clear()
    EventBus._handlers.update(original_handlers)
    EventBus._bootstrapped = original_bootstrapped


def test_register_adds_handler():
    EventBus.register("test.event", "my.module.task")
    assert "my.module.task" in EventBus._handlers["test.event"]


def test_register_deduplicate_handlers():
    EventBus.register("test.event", "my.module.task")
    EventBus.register("test.event", "my.module.task")
    assert EventBus._handlers["test.event"].count("my.module.task") == 1


def test_get_handlers_bootstraps_and_returns_handlers():
    EventBus._bootstrapped = False
    handlers = EventBus.get_handlers(RECORD_STORED)
    assert "talk2record.audit.tasks.handle_domain_event_for_audit" in handlers
    assert "talk2record.analytics.tasks.handle_domain_event_for_analytics" in handlers
    assert (
        "talk2record.notifications.tasks.handle_domain_event_for_notifications"
        in handlers
    )


def test_get_handlers_returns_empty_for_unknown_event():
    EventBus._bootstrapped = True
    handlers = EventBus.get_handlers("unknown.event")
    assert handlers == []


def test_register_defaults_covers_all_expected_events():
    from talk2record.events.names import AI_EXTRACTION_COMPLETED
    from talk2record.events.names import AI_TRANSCRIPTION_COMPLETED
    from talk2record.events.names import BILLING_LIMIT_EXCEEDED
    from talk2record.events.names import INGESTION_RECEIVED
    from talk2record.events.names import RECORD_PROCESSING_COMPLETED
    from talk2record.events.names import RECORD_PROCESSING_FAILED
    from talk2record.events.names import RECORD_PROCESSING_STARTED
    from talk2record.events.names import USAGE_AI_INCREMENTED

    registered: dict[str, list[str]] = {}
    register_defaults(lambda name, task: registered.setdefault(name, []).append(task))

    assert RECORD_STORED in registered
    assert LEGAL_ACCEPTED in registered
    assert "record.created" in registered
    assert INGESTION_RECEIVED in registered
    assert "billing.payment_failed" in registered
    assert "billing.subscription_created" in registered
    assert AI_EXTRACTION_COMPLETED in registered
    assert AI_TRANSCRIPTION_COMPLETED in registered

    # New lifecycle events
    assert RECORD_PROCESSING_STARTED in registered
    assert RECORD_PROCESSING_COMPLETED in registered
    assert RECORD_PROCESSING_FAILED in registered
    assert USAGE_AI_INCREMENTED in registered
    assert BILLING_LIMIT_EXCEEDED in registered


@pytest.mark.django_db
def test_publish_persists_domain_event(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    event = DomainEvent(
        name=RECORD_STORED,
        organization_id=1,
        user_id=1,
        resource_type="record",
        resource_id="1",
        metadata={"source": "test"},
    )
    EventBus.publish(event)
    assert DomainEventRecord.objects.filter(id=event.event_id).exists()


@pytest.mark.django_db(transaction=True)
def test_publish_after_commit_persists_event(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    event = DomainEvent(
        name=RECORD_STORED,
        organization_id=None,
        user_id=None,
        resource_type="record",
        resource_id="test",
    )
    from django.db import transaction

    with transaction.atomic():
        publish_after_commit(event)

    assert DomainEventRecord.objects.filter(name=RECORD_STORED).exists()
