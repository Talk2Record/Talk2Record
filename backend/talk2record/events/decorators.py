from __future__ import annotations

from talk2record.events.idempotency import claim_event


def already_handled(event_payload: dict, handler_name: str) -> bool:
    """
    Return True when this event has already been processed by handler_name,
    meaning the caller should return early.  Returns False when the event is
    claimed successfully and the handler should proceed.

    Usage::

        if already_handled(event_payload, "audit"):
            return
    """
    event_id = str(event_payload.get("event_id", ""))
    if not event_id:
        return True
    return not claim_event(event_id, handler_name)
