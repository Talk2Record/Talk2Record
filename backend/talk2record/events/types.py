from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DomainEvent:
    name: str
    organization_id: int | None
    user_id: int | None
    resource_type: str | None
    resource_id: str | None
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    event_id: str = field(default_factory=lambda: str(uuid4()))

    def to_payload(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "metadata": dict(self.metadata),
            "occurred_at": self.occurred_at.isoformat(),
        }
