from __future__ import annotations

from django.core.cache import cache

IDEMPOTENCY_TTL_SECONDS = 60 * 60 * 24 * 7
KEY_PREFIX = "events:processed"


def claim_event(event_id: str, handler_name: str) -> bool:
    """
    Claim event processing for a handler.

    Returns True when this handler should process the event, and False
    when the event has already been claimed before.
    """
    key = f"{KEY_PREFIX}:{handler_name}:{event_id}"
    return bool(cache.add(key, "1", timeout=IDEMPOTENCY_TTL_SECONDS))
