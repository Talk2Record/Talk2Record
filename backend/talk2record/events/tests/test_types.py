from __future__ import annotations

from datetime import UTC

from talk2record.events.types import DomainEvent


def test_domain_event_to_payload_round_trip():
    event = DomainEvent(
        name="record.stored",
        organization_id=1,
        user_id=42,
        resource_type="record",
        resource_id="99",
        metadata={"source": "whatsapp", "status": "stored"},
    )
    payload = event.to_payload()

    assert payload["name"] == "record.stored"
    assert payload["organization_id"] == 1
    assert payload["user_id"] == 42
    assert payload["resource_type"] == "record"
    assert payload["resource_id"] == "99"
    assert payload["metadata"] == {"source": "whatsapp", "status": "stored"}
    assert "event_id" in payload
    assert "occurred_at" in payload
    assert payload["event_id"] == event.event_id


def test_domain_event_to_payload_metadata_is_copy():
    event = DomainEvent(
        name="record.stored",
        organization_id=None,
        user_id=None,
        resource_type=None,
        resource_id=None,
        metadata={"key": "value"},
    )
    payload = event.to_payload()
    payload["metadata"]["mutated"] = True
    assert "mutated" not in event.metadata


def test_domain_event_default_occurred_at_is_utc():
    event = DomainEvent(
        name="record.stored",
        organization_id=None,
        user_id=None,
        resource_type=None,
        resource_id=None,
    )
    assert event.occurred_at.tzinfo is not None
    assert event.occurred_at.tzinfo == UTC


def test_domain_event_unique_event_ids():
    e1 = DomainEvent(
        name="record.stored",
        organization_id=None,
        user_id=None,
        resource_type=None,
        resource_id=None,
    )
    e2 = DomainEvent(
        name="record.stored",
        organization_id=None,
        user_id=None,
        resource_type=None,
        resource_id=None,
    )
    assert e1.event_id != e2.event_id
