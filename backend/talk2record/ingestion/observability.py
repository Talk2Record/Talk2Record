from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from django.http import HttpRequest

logger = logging.getLogger("talk2record.ingestion")


def request_id_from_request(request: HttpRequest) -> str:
    header_value = request.headers.get("X-Request-ID", "").strip()
    if header_value:
        return header_value
    return str(uuid4())


def new_event_id() -> str:
    return str(uuid4())


def log_ingestion_event(action: str, **fields: object) -> None:
    payload = {"action": action, **fields}
    logger.info(json.dumps(payload, default=str, sort_keys=True))
