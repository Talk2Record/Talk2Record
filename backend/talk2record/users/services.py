from __future__ import annotations

from django.db import transaction
from django.utils import timezone
from slugify import slugify

from talk2record.audit.services import AuditService
from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import USER_REGISTERED
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.services import LegalAcceptanceService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.users.models import User


class RegistrationService:
    @staticmethod
    @transaction.atomic
    def register_user(
        *,
        email: str,
        password: str,
        name: str,
        company: str,
        accepted_document_keys: list[str],
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> User:
        user = User.objects.create_user(email=email, password=password, name=name)
        organization = Organization.objects.create(
            name=company,
            slug=RegistrationService._build_unique_slug(company),
        )
        Membership.objects.create(
            user=user,
            organization=organization,
            role=Membership.Role.OWNER,
            status=Membership.Status.ACTIVE,
        )
        user.current_organization = organization
        user.latest_required_legal_acceptance_at = timezone.now()
        user.save(update_fields=["current_organization", "latest_required_legal_acceptance_at"])
        LegalAcceptanceService.accept_documents(
            user=user,
            document_keys=accepted_document_keys,
            source=UserLegalAcceptance.Source.SIGNUP,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        AuditService.log(
            action="user.registered",
            resource_type="user",
            resource_id=str(user.pk),
            actor=user,
            organization=organization,
            metadata={"documents": accepted_document_keys},
        )
        publish_after_commit(
            DomainEvent(
                name=USER_REGISTERED,
                organization_id=organization.id,
                user_id=user.id,
                resource_type="user",
                resource_id=str(user.pk),
                metadata={"documents": accepted_document_keys},
            ),
        )
        return user

    @staticmethod
    def ensure_required_signup_documents(document_keys: list[str]) -> None:
        required_document_keys = {
            version.document_key
            for version in LegalAcceptanceService.get_required_signup_versions()
        }
        if not required_document_keys.issubset(set(document_keys)):
            msg = "Required legal documents must be accepted before registration."
            raise ValueError(msg)

    @staticmethod
    def _build_unique_slug(company: str) -> str:
        base_slug = slugify(company) or "workspace"
        slug = base_slug
        suffix = 1
        while Organization.objects.filter(slug=slug).exists():
            suffix += 1
            slug = f"{base_slug}-{suffix}"
        return slug
