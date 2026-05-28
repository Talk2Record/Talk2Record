from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.core.cache import cache

from talk2record.audit.models import AuditLog

if TYPE_CHECKING:
    from collections.abc import Mapping


class AuditService:
    ACTION_API_KEY_USED = "organization.api_key.used"
    RESOURCE_TYPE_API_KEY = "organization_api_key"
    CACHE_KEY_PREFIX = "audit:api_key_used:"

    @staticmethod
    def log(  # noqa: PLR0913
        *,
        action: str,
        resource_type: str,
        resource_id: str = "",
        actor=None,
        organization=None,
        metadata: Mapping[str, object] | None = None,
    ) -> AuditLog:
        return AuditLog.objects.create(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor=actor,
            organization=organization,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def log_api_key_used_if_sampled(
        cls,
        *,
        api_key_id: int,
        actor=None,
        organization=None,
        metadata: Mapping[str, object] | None = None,
    ) -> AuditLog | None:
        interval_min = getattr(
            settings,
            "AUDIT_API_KEY_USED_SAMPLE_INTERVAL_MINUTES",
            5,
        )
        cache_key = f"{cls.CACHE_KEY_PREFIX}{api_key_id}"
        if interval_min > 0:
            if cache.get(cache_key):
                return None
            cache.set(cache_key, "1", timeout=interval_min * 60)
        return cls.log(
            action=cls.ACTION_API_KEY_USED,
            resource_type=cls.RESOURCE_TYPE_API_KEY,
            resource_id=str(api_key_id),
            actor=actor,
            organization=organization,
            metadata=dict(metadata or {}),
        )
