"""Membership invitation flow.

Accept-token format:

    <invitation_id>.<raw_secret>

where ``raw_secret`` is 32 bytes of ``secrets.token_urlsafe`` output. Only the
SHA-256 of the full token is persisted on :class:`MembershipInvitation`, so the
raw token is unrecoverable after creation and usable exactly once.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import MEMBERSHIP_ACCEPTED
from talk2record.events.names import MEMBERSHIP_INVITED
from talk2record.events.names import MEMBERSHIP_REMOVED
from talk2record.events.names import MEMBERSHIP_REVOKED
from talk2record.events.names import MEMBERSHIP_ROLE_CHANGED
from talk2record.organizations.models import Membership
from talk2record.organizations.models import MembershipInvitation
from talk2record.organizations.models import Organization
from talk2record.users.models import User

INVITE_TTL_DAYS = 7
INVITE_SECRET_BYTES = 32


@dataclass(frozen=True)
class CreatedInvitation:
    invitation: MembershipInvitation
    raw_token: str
    """Format: ``<invitation_id>.<secret>``. Show/email exactly once."""


class InvitationError(Exception):
    """Raised when an invitation cannot be accepted or created."""


class MembershipInvitationService:
    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    @staticmethod
    def _build_raw_token(invitation_id: int, secret: str) -> str:
        return f"{invitation_id}.{secret}"

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        organization: Organization,
        email: str,
        role: str,
        invited_by: User | None = None,
        ttl_days: int = INVITE_TTL_DAYS,
    ) -> CreatedInvitation:
        email = email.strip().lower()
        if not email:
            raise InvitationError("Email is required.")
        if role not in dict(Membership.Role.choices):
            raise InvitationError(f"Invalid role: {role}")

        existing_member = Membership.objects.filter(
            organization=organization,
            user__email__iexact=email,
        ).exists()
        if existing_member:
            raise InvitationError("User is already a member of this organization.")

        MembershipInvitation.objects.filter(
            organization=organization,
            email__iexact=email,
            status=MembershipInvitation.Status.PENDING,
        ).update(
            status=MembershipInvitation.Status.REVOKED,
            revoked_at=timezone.now(),
        )

        secret = secrets.token_urlsafe(INVITE_SECRET_BYTES)
        expires_at = timezone.now() + timedelta(days=ttl_days)

        placeholder_hash = secrets.token_hex(32)
        invitation = MembershipInvitation.objects.create(
            organization=organization,
            email=email,
            role=role,
            token_hash=placeholder_hash,
            invited_by=invited_by,
            expires_at=expires_at,
        )
        raw_token = cls._build_raw_token(invitation.pk, secret)
        invitation.token_hash = cls._hash_token(raw_token)
        invitation.save(update_fields=["token_hash", "updated_at"])

        publish_after_commit(
            DomainEvent(
                name=MEMBERSHIP_INVITED,
                organization_id=organization.pk,
                user_id=invited_by.pk if invited_by else None,
                resource_type="membership_invitation",
                resource_id=str(invitation.pk),
                metadata={
                    "email": email,
                    "role": role,
                    "expires_at": expires_at.isoformat(),
                },
            ),
        )
        return CreatedInvitation(invitation=invitation, raw_token=raw_token)

    @classmethod
    def revoke(
        cls,
        *,
        invitation: MembershipInvitation,
        actor: User | None = None,
    ) -> MembershipInvitation:
        if invitation.status != MembershipInvitation.Status.PENDING:
            raise InvitationError("Only pending invitations can be revoked.")
        invitation.status = MembershipInvitation.Status.REVOKED
        invitation.revoked_at = timezone.now()
        invitation.save(update_fields=["status", "revoked_at", "updated_at"])
        publish_after_commit(
            DomainEvent(
                name=MEMBERSHIP_REVOKED,
                organization_id=invitation.organization_id,
                user_id=actor.pk if actor else None,
                resource_type="membership_invitation",
                resource_id=str(invitation.pk),
                metadata={"email": invitation.email},
            ),
        )
        return invitation

    @classmethod
    def find_by_token(cls, raw_token: str) -> MembershipInvitation | None:
        if not raw_token or "." not in raw_token:
            return None
        invitation_id_str, _secret = raw_token.split(".", 1)
        try:
            invitation_id = int(invitation_id_str)
        except ValueError:
            return None
        invitation = (
            MembershipInvitation.objects.select_related("organization")
            .filter(pk=invitation_id)
            .first()
        )
        if invitation is None:
            return None
        if not hmac.compare_digest(invitation.token_hash, cls._hash_token(raw_token)):
            return None
        return invitation

    @classmethod
    @transaction.atomic
    def accept(cls, *, raw_token: str, user: User) -> Membership:
        invitation = cls.find_by_token(raw_token)
        if invitation is None:
            raise InvitationError("Invalid invitation token.")
        if invitation.status != MembershipInvitation.Status.PENDING:
            raise InvitationError("This invitation is no longer pending.")
        if invitation.expires_at <= timezone.now():
            invitation.status = MembershipInvitation.Status.EXPIRED
            invitation.save(update_fields=["status", "updated_at"])
            raise InvitationError("This invitation has expired.")
        if user.email.lower() != invitation.email.lower():
            raise InvitationError(
                "This invitation was issued to a different email address.",
            )

        membership, created = Membership.objects.get_or_create(
            user=user,
            organization=invitation.organization,
            defaults={
                "role": invitation.role,
                "status": Membership.Status.ACTIVE,
            },
        )
        if not created:
            membership.status = Membership.Status.ACTIVE
            membership.role = invitation.role
            membership.save(update_fields=["status", "role", "updated_at"])

        if user.current_organization_id is None:
            user.current_organization = invitation.organization
            user.save(update_fields=["current_organization"])

        invitation.status = MembershipInvitation.Status.ACCEPTED
        invitation.accepted_by = user
        invitation.accepted_at = timezone.now()
        invitation.save(
            update_fields=["status", "accepted_by", "accepted_at", "updated_at"],
        )

        publish_after_commit(
            DomainEvent(
                name=MEMBERSHIP_ACCEPTED,
                organization_id=invitation.organization_id,
                user_id=user.pk,
                resource_type="membership",
                resource_id=str(membership.pk),
                metadata={"invitation_id": invitation.pk, "role": membership.role},
            ),
        )
        return membership

    @classmethod
    def change_role(
        cls,
        *,
        membership: Membership,
        new_role: str,
        actor: User | None = None,
    ) -> Membership:
        if new_role not in dict(Membership.Role.choices):
            raise InvitationError(f"Invalid role: {new_role}")
        if membership.role == new_role:
            return membership
        previous_role = membership.role
        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])
        publish_after_commit(
            DomainEvent(
                name=MEMBERSHIP_ROLE_CHANGED,
                organization_id=membership.organization_id,
                user_id=actor.pk if actor else None,
                resource_type="membership",
                resource_id=str(membership.pk),
                metadata={
                    "previous_role": previous_role,
                    "role": new_role,
                    "member_user_id": membership.user_id,
                },
            ),
        )
        return membership

    @classmethod
    @transaction.atomic
    def remove(
        cls,
        *,
        membership: Membership,
        actor: User | None = None,
    ) -> None:
        if membership.role == Membership.Role.OWNER:
            other_owners = Membership.objects.filter(
                organization=membership.organization,
                role=Membership.Role.OWNER,
            ).exclude(pk=membership.pk).exists()
            if not other_owners:
                raise InvitationError("Cannot remove the last owner of the organization.")
        organization_id = membership.organization_id
        user_id = membership.user_id
        membership.delete()
        publish_after_commit(
            DomainEvent(
                name=MEMBERSHIP_REMOVED,
                organization_id=organization_id,
                user_id=actor.pk if actor else None,
                resource_type="user",
                resource_id=str(user_id),
                metadata={},
            ),
        )


def build_invitation_accept_url(raw_token: str) -> str:
    base = getattr(settings, "FRONTEND_URL", "") or getattr(settings, "SITE_URL", "")
    base = str(base).rstrip("/") or ""
    return f"{base}/invite/{raw_token}"
