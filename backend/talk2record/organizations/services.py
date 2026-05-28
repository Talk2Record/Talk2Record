from __future__ import annotations

import hashlib
import hmac
import math
import secrets
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.organizations.models import OrganizationAPIKey

if TYPE_CHECKING:
    from talk2record.users.models import User


@dataclass(frozen=True)
class ResolvedOrganizationContext:
    organization: Organization
    role: str


class OrganizationContextService:
    @staticmethod
    def resolve_user_context(user: User) -> ResolvedOrganizationContext | None:
        organization = user.current_organization
        if organization is None:
            membership = user.memberships.select_related("organization").first()
            if membership:
                organization = membership.organization
        if organization is None:
            return None

        membership = (
            Membership.objects.filter(user=user, organization=organization)
            .only("role")
            .first()
        )
        role = membership.role if membership else Membership.Role.OPERATOR
        return ResolvedOrganizationContext(organization=organization, role=role)


class OrganizationAPIKeyService:
    KEY_PREFIX_LENGTH = 12
    KEY_SECRET_BYTES = 24
    KEY_LABEL_PREFIX = "t2r"
    DEFAULT_SCOPE = "ingestion:write"
    KEY_PART_COUNT = 3
    SCOPE_PRESETS = {
        "ingestion": [DEFAULT_SCOPE],
        "ingestion_plus_read": [DEFAULT_SCOPE, "records:read"],
    }

    @classmethod
    def create_key(  # noqa: PLR0913
        cls,
        *,
        organization: Organization,
        name: str,
        scopes: list[str] | None = None,
        scope_preset: str | None = None,
        rate_limit_per_minute: int | None = None,
        created_by: User | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[OrganizationAPIKey, str]:
        secret = secrets.token_hex(cls.KEY_SECRET_BYTES)
        prefix = secret[: cls.KEY_PREFIX_LENGTH]
        raw_key = f"{cls.KEY_LABEL_PREFIX}_{prefix}_{secret}"
        key_hash = cls._hash_key(raw_key)
        resolved_scopes = cls.resolve_scopes(scopes=scopes, scope_preset=scope_preset)
        api_key = OrganizationAPIKey.objects.create(
            organization=organization,
            created_by=created_by,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=resolved_scopes,
            rate_limit_per_minute=rate_limit_per_minute,
            expires_at=(
                timezone.now() + timedelta(days=expires_in_days)
                if expires_in_days is not None
                else None
            ),
        )
        return api_key, raw_key

    @classmethod
    def resolve_active_key(
        cls,
        raw_key: str,
        *,
        required_scope: str | None = None,
    ) -> OrganizationAPIKey | None:
        parsed = cls._parse_key(raw_key)
        if parsed is None:
            return None
        prefix, normalized_key = parsed
        candidate_keys = OrganizationAPIKey.objects.filter(
            key_prefix=prefix,
            is_active=True,
        ).select_related("organization", "created_by")
        candidate_hash = cls._hash_key(normalized_key)
        for candidate in candidate_keys:
            if not hmac.compare_digest(candidate.key_hash, candidate_hash):
                continue
            if required_scope and required_scope not in candidate.scopes:
                return None
            if candidate.expires_at and candidate.expires_at <= timezone.now():
                return None
            return candidate
        return None

    @classmethod
    def record_key_usage(
        cls,
        *,
        api_key: OrganizationAPIKey,
        ip_address: str = "",
        user_agent: str = "",
    ) -> None:
        api_key.last_used_at = timezone.now()
        api_key.last_used_ip = ip_address
        api_key.last_used_user_agent = user_agent[:255]
        api_key.save(
            update_fields=[
                "last_used_at",
                "last_used_ip",
                "last_used_user_agent",
                "updated_at",
            ],
        )

    @classmethod
    def revoke_key(cls, api_key: OrganizationAPIKey) -> None:
        api_key.is_active = False
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["is_active", "revoked_at", "updated_at"])

    @classmethod
    def rotate_key(
        cls,
        *,
        api_key: OrganizationAPIKey,
        rotated_by: User | None = None,
    ) -> tuple[OrganizationAPIKey, str]:
        expires_in_days = None
        if api_key.expires_at:
            remaining_seconds = (api_key.expires_at - timezone.now()).total_seconds()
            if remaining_seconds > 0:
                expires_in_days = max(1, math.ceil(remaining_seconds / 86400))
        replacement, raw_key = cls.create_key(
            organization=api_key.organization,
            name=f"{api_key.name} (rotated)",
            scopes=list(api_key.scopes),
            rate_limit_per_minute=api_key.rate_limit_per_minute,
            created_by=rotated_by or api_key.created_by,
            expires_in_days=expires_in_days,
        )
        cls.revoke_key(api_key)
        return replacement, raw_key

    @classmethod
    def resolve_scopes(
        cls,
        *,
        scopes: list[str] | None,
        scope_preset: str | None,
    ) -> list[str]:
        if scope_preset:
            return list(cls.SCOPE_PRESETS.get(scope_preset, [cls.DEFAULT_SCOPE]))
        return scopes or [cls.DEFAULT_SCOPE]

    @classmethod
    def _hash_key(cls, raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def _parse_key(cls, raw_key: str) -> tuple[str, str] | None:
        normalized = raw_key.strip()
        pieces = normalized.split("_")
        if len(pieces) != cls.KEY_PART_COUNT:
            return None
        label, prefix, _secret = pieces
        if label != cls.KEY_LABEL_PREFIX:
            return None
        if len(prefix) != cls.KEY_PREFIX_LENGTH:
            return None
        return prefix, normalized
