from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime

import pytest

from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import RECORD_STORED


@pytest.mark.django_db
def test_unprocessed_events_can_be_queried():
    event_id_1 = str(uuid.uuid4())
    event_id_2 = str(uuid.uuid4())

    DomainEventRecord.objects.create(
        id=event_id_1,
        name=RECORD_STORED,
        occurred_at=datetime.now(tz=UTC),
        processed=False,
    )
    DomainEventRecord.objects.create(
        id=event_id_2,
        name=RECORD_STORED,
        occurred_at=datetime.now(tz=UTC),
        processed=True,
    )

    unprocessed = DomainEventRecord.objects.filter(processed=False)
    assert unprocessed.count() == 1
    assert str(unprocessed.first().id) == event_id_1


@pytest.mark.django_db(transaction=True)
def test_replay_unprocessed_events_via_dispatch(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    event_id = str(uuid.uuid4())

    DomainEventRecord.objects.create(
        id=event_id,
        name=RECORD_STORED,
        organization_id=None,
        user_id=None,
        resource_type="record",
        resource_id="1",
        payload={
            "event_id": event_id,
            "name": RECORD_STORED,
            "organization_id": None,
            "user_id": None,
            "resource_type": "record",
            "resource_id": "1",
            "metadata": {},
            "occurred_at": datetime.now(tz=UTC).isoformat(),
        },
        occurred_at=datetime.now(tz=UTC),
        processed=False,
    )

    from talk2record.events.tasks import dispatch_domain_event

    unprocessed_events = DomainEventRecord.objects.filter(processed=False)
    for event in unprocessed_events:
        dispatch_domain_event(event.payload)

    event = DomainEventRecord.objects.get(id=event_id)
    assert event.processed is True


@pytest.mark.django_db(transaction=True)
def test_replay_is_idempotent(settings):
    """Re-dispatching an already-processed event does not double-process handlers."""
    settings.CELERY_TASK_ALWAYS_EAGER = True
    event_id = str(uuid.uuid4())

    from talk2record.audit.models import AuditLog

    DomainEventRecord.objects.create(
        id=event_id,
        name=RECORD_STORED,
        organization_id=None,
        resource_type="record",
        resource_id="1",
        payload={
            "event_id": event_id,
            "name": RECORD_STORED,
            "organization_id": None,
            "user_id": None,
            "resource_type": "record",
            "resource_id": "1",
            "metadata": {},
            "occurred_at": datetime.now(tz=UTC).isoformat(),
        },
        occurred_at=datetime.now(tz=UTC),
        processed=False,
    )

    from talk2record.events.tasks import dispatch_domain_event

    payload = DomainEventRecord.objects.get(id=event_id).payload

    dispatch_domain_event(payload)
    dispatch_domain_event(payload)

    assert (
        AuditLog.objects.filter(
            action=RECORD_STORED,
            resource_id="1",
        ).count()
        == 1
    )
