from __future__ import annotations

import uuid

import pytest

from talk2record.events.idempotency import claim_event


@pytest.mark.django_db
def test_claim_event_returns_true_first_call():
    event_id = str(uuid.uuid4())
    assert claim_event(event_id, "analytics") is True


@pytest.mark.django_db
def test_claim_event_returns_false_on_repeat():
    event_id = str(uuid.uuid4())
    assert claim_event(event_id, "analytics") is True
    assert claim_event(event_id, "analytics") is False


@pytest.mark.django_db
def test_claim_event_different_handlers_are_independent():
    event_id = str(uuid.uuid4())
    assert claim_event(event_id, "analytics") is True
    assert claim_event(event_id, "audit") is True


@pytest.mark.django_db
def test_claim_event_different_event_ids_are_independent():
    event_id_1 = str(uuid.uuid4())
    event_id_2 = str(uuid.uuid4())
    assert claim_event(event_id_1, "analytics") is True
    assert claim_event(event_id_2, "analytics") is True
