from __future__ import annotations

import pytest

from talk2record.events.decorators import already_handled


@pytest.mark.django_db
def test_already_handled_returns_false_first_time(db):
    payload = {"event_id": "unique-evt-001", "name": "test.event"}
    assert already_handled(payload, "test_handler") is False


@pytest.mark.django_db
def test_already_handled_returns_true_on_repeat(db):
    payload = {"event_id": "unique-evt-002", "name": "test.event"}
    assert already_handled(payload, "test_handler") is False
    assert already_handled(payload, "test_handler") is True


@pytest.mark.django_db
def test_already_handled_different_handlers_are_independent(db):
    payload = {"event_id": "unique-evt-003", "name": "test.event"}
    assert already_handled(payload, "handler_a") is False
    assert already_handled(payload, "handler_b") is False


@pytest.mark.django_db
def test_already_handled_returns_true_when_event_id_missing(db):
    assert already_handled({}, "test_handler") is True
    assert already_handled({"name": "test.event"}, "test_handler") is True
