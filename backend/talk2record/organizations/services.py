from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
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

    @classmethod
    def create_key(
        cls,
        *,
        organization: Organization,
        name: str,
        scopes: list[str] | None = None,
        created_by: User | None = None,
    ) -> tuple[OrganizationAPIKey, str]:
        secret = secrets.token_hex(cls.KEY_SECRET_BYTES)
        prefix = secret[: cls.KEY_PREFIX_LENGTH]
        raw_key = f"{cls.KEY_LABEL_PREFIX}_{prefix}_{secret}"
        key_hash = cls._hash_key(raw_key)
        api_key = OrganizationAPIKey.objects.create(
            organization=organization,
            created_by=created_by,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=scopes or [cls.DEFAULT_SCOPE],
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
            candidate.last_used_at = timezone.now()
            candidate.save(update_fields=["last_used_at", "updated_at"])
            return candidate
        return None

    @classmethod
    def revoke_key(cls, api_key: OrganizationAPIKey) -> None:
        api_key.is_active = False
        api_key.save(update_fields=["is_active", "updated_at"])

    @classmethod
    def _hash_key(cls, raw_key: str) -> str:
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    @classmethod
    def _parse_key(cls, raw_key: str) -> tuple[str, str] | None:
        normalized = raw_key.strip()
        pieces = normalized.split("_")
        if len(pieces) != 3:
            return None
        label, prefix, _secret = pieces
        if label != cls.KEY_LABEL_PREFIX:
            return None
        if len(prefix) != cls.KEY_PREFIX_LENGTH:
            return None
        return prefix, normalized
