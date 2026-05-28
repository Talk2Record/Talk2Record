from __future__ import annotations

import uuid
from datetime import UTC
from datetime import datetime

import pytest

from talk2record.events.models import DomainEvent as DomainEventRecord


@pytest.mark.django_db
def test_domain_event_model_creation():
    event_id = str(uuid.uuid4())
    event = DomainEventRecord.objects.create(
        id=event_id,
        name="record.stored",
        organization_id=1,
        user_id=42,
        resource_type="record",
        resource_id="99",
        payload={"source": "whatsapp"},
        occurred_at=datetime.now(tz=UTC),
    )
    assert str(event.id) == event_id
    assert event.name == "record.stored"
    assert event.organization_id == 1
    assert event.processed is False
    assert event.created_at is not None


@pytest.mark.django_db
def test_domain_event_model_str():
    event_id = str(uuid.uuid4())
    event = DomainEventRecord.objects.create(
        id=event_id,
        name="record.stored",
        occurred_at=datetime.now(tz=UTC),
    )
    assert str(event) == f"record.stored:{event_id}"


@pytest.mark.django_db
def test_domain_event_model_indexes():
    # Verify the model has the expected index fields by checking Meta.indexes
    index_fields = {tuple(idx.fields) for idx in DomainEventRecord._meta.indexes}
    assert ("name",) in index_fields
    assert ("organization_id",) in index_fields
    assert ("created_at",) in index_fields
    assert ("processed",) in index_fields


@pytest.mark.django_db
def test_domain_event_model_processed_default_false():
    event = DomainEventRecord.objects.create(
        name="user.registered",
        occurred_at=datetime.now(tz=UTC),
    )
    assert event.processed is False


@pytest.mark.django_db
def test_domain_event_model_can_be_marked_processed():
    event = DomainEventRecord.objects.create(
        name="record.stored",
        occurred_at=datetime.now(tz=UTC),
    )
    DomainEventRecord.objects.filter(id=event.id).update(processed=True)
    event.refresh_from_db()
    assert event.processed is True
