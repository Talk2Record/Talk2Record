from __future__ import annotations

from collections.abc import Iterable

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from talk2record.analytics.services import AnalyticsService
from talk2record.audit.services import AuditService
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation

DEFAULT_LEGAL_DOCUMENTS = {
    LegalDocumentVersion.DocumentKey.PRIVACY_POLICY: {
        "version": "2026-03-18",
        "title": "Privacy Policy",
        "summary": "How Talk2Record processes personal data.",
        "required_at_signup": True,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE: {
        "version": "2026-03-18",
        "title": "Terms of Service",
        "summary": "Contractual terms for using Talk2Record.",
        "required_at_signup": True,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.DATA_PROCESSING_AGREEMENT: {
        "version": "2026-03-18",
        "title": "Data Processing Agreement",
        "summary": "Processor terms for customer personal data.",
        "required_at_signup": False,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.AI_USAGE_AND_DISCLAIMER: {
        "version": "2026-03-18",
        "title": "AI Usage and Disclaimer",
        "summary": "Limits and review expectations for AI outputs.",
        "required_at_signup": False,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.COOKIE_POLICY: {
        "version": "2026-03-18",
        "title": "Cookie Policy",
        "summary": "Cookie and tracking disclosures.",
        "required_at_signup": False,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.ACCEPTABLE_USE_POLICY: {
        "version": "2026-03-18",
        "title": "Acceptable Use Policy",
        "summary": "Prohibited activities on Talk2Record.",
        "required_at_signup": False,
        "required_for_billing": False,
    },
    LegalDocumentVersion.DocumentKey.BILLING_POLICY: {
        "version": "2026-03-18",
        "title": "Billing Policy",
        "summary": "Billing, renewals, refunds, and failed payments.",
        "required_at_signup": False,
        "required_for_billing": True,
    },
}


class LegalAcceptanceService:
    @staticmethod
    def sync_default_versions() -> None:
        if LegalDocumentVersion.objects.exists():
            return
        effective_at = timezone.now()
        for document_key, config in DEFAULT_LEGAL_DOCUMENTS.items():
            LegalDocumentVersion.objects.create(
                document_key=document_key,
                version=config["version"],
                title=config["title"],
                summary=config["summary"],
                required_at_signup=config["required_at_signup"],
                required_for_billing=config["required_for_billing"],
                effective_at=effective_at,
            )

    @staticmethod
    def get_active_versions() -> dict[str, LegalDocumentVersion]:
        LegalAcceptanceService.sync_default_versions()
        versions = (
            LegalDocumentVersion.objects.filter(is_active=True)
            .order_by("document_key", "-effective_at", "-pk")
        )
        current_versions: dict[str, LegalDocumentVersion] = {}
        for version in versions:
            current_versions.setdefault(version.document_key, version)
        return current_versions

    @classmethod
    def get_required_signup_versions(cls) -> list[LegalDocumentVersion]:
        return [
            version
            for version in cls.get_active_versions().values()
            if version.required_at_signup
        ]

    @classmethod
    def get_required_billing_versions(cls) -> list[LegalDocumentVersion]:
        return [
            version
            for version in cls.get_active_versions().values()
            if version.required_for_billing
        ]

    @staticmethod
    def get_user_compliance(user) -> dict[str, object]:
        acceptances = (
            UserLegalAcceptance.objects.filter(user=user)
            .values("document_version__document_key")
            .annotate(latest_accepted_at=Max("accepted_at"))
        )
        accepted_documents = {
            item["document_version__document_key"]: item["latest_accepted_at"]
            for item in acceptances
        }
        current_versions = LegalAcceptanceService.get_active_versions()
        required_signup = [
            version.document_key
            for version in current_versions.values()
            if version.required_at_signup
        ]
        required_billing = [
            version.document_key
            for version in current_versions.values()
            if version.required_for_billing
        ]
        return {
            "accepted_documents": [
                {
                    "documentKey": version.document_key,
                    "version": version.version,
                    "acceptedAt": accepted_documents.get(version.document_key),
                }
                for version in current_versions.values()
            ],
            "required_signup_documents": required_signup,
            "required_billing_documents": required_billing,
            "has_required_signup_acceptance": all(
                accepted_documents.get(document_key) is not None
                for document_key in required_signup
            ),
            "has_required_billing_acceptance": all(
                accepted_documents.get(document_key) is not None
                for document_key in required_billing
            ),
        }

    @classmethod
    @transaction.atomic
    def accept_documents(
        cls,
        *,
        user,
        document_keys: Iterable[str],
        source: str,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> list[UserLegalAcceptance]:
        current_versions = cls.get_active_versions()
        acceptances: list[UserLegalAcceptance] = []
        for document_key in document_keys:
            document_version = current_versions[document_key]
            acceptance = UserLegalAcceptance.objects.create(
                user=user,
                document_version=document_version,
                acceptance_source=source,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            acceptances.append(acceptance)

        if acceptances:
            user.latest_required_legal_acceptance_at = timezone.now()
            user.save(update_fields=["latest_required_legal_acceptance_at"])
            AuditService.log(
                action="legal.accepted",
                resource_type="legal_document",
                actor=user,
                organization=user.current_organization,
                metadata={
                    "document_keys": list(document_keys),
                    "source": source,
                },
            )
            AnalyticsService.track_event(
                name="legal_documents_accepted",
                category="legal",
                organization=user.current_organization,
                properties={"count": len(acceptances), "source": source},
            )
        return acceptances

    @staticmethod
    def record_attestation(
        *,
        user,
        kind: str,
        context: str,
        metadata: dict[str, object] | None = None,
        ip_address: str | None = None,
        user_agent: str = "",
    ) -> UserLegalAttestation:
        attestation = UserLegalAttestation.objects.create(
            user=user,
            kind=kind,
            context=context,
            metadata=metadata or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        AuditService.log(
            action="legal.attested",
            resource_type="legal_attestation",
            actor=user,
            organization=user.current_organization,
            resource_id=str(attestation.pk),
            metadata={"kind": kind, "context": context},
        )
        AnalyticsService.track_event(
            name="legal_attestation_recorded",
            category="legal",
            organization=user.current_organization,
            properties={"kind": kind, "context": context},
        )
        return attestation
