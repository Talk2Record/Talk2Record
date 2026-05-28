from __future__ import annotations

from typing import TYPE_CHECKING

from talk2record.analytics.models import Event

if TYPE_CHECKING:
    from collections.abc import Mapping


class AnalyticsService:
    @staticmethod
    def track_event(
        *,
        name: str,
        category: str,
        organization=None,
        properties: Mapping[str, object] | None = None,
    ) -> Event:
        return Event.objects.create(
            name=name,
            category=category,
            organization=organization,
            properties=dict(properties or {}),
        )
