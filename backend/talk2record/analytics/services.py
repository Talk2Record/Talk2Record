from __future__ import annotations

from collections.abc import Mapping

from talk2record.analytics.models import Event


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
