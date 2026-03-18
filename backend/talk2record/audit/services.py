from __future__ import annotations

from collections.abc import Mapping

from talk2record.audit.models import AuditLog


class AuditService:
    @staticmethod
    def log(
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
