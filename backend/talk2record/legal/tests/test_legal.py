from http import HTTPStatus

import pytest
from django.urls import reverse

from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService


@pytest.mark.django_db
def test_sync_default_versions_creates_documents():
    LegalAcceptanceService.sync_default_versions()

    assert LegalDocumentVersion.objects.count() == 7
    terms = LegalDocumentVersion.objects.get(
        document_key=LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE,
    )
    assert str(terms) == f"Terms of Service ({terms.version})"


@pytest.mark.django_db
def test_accept_documents_records_acceptance(workspace_user, legal_versions):
    acceptances = LegalAcceptanceService.accept_documents(
        user=workspace_user,
        document_keys=[
            LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE,
            LegalDocumentVersion.DocumentKey.PRIVACY_POLICY,
        ],
        source=UserLegalAcceptance.Source.SIGNUP,
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    workspace_user.refresh_from_db()
    assert len(acceptances) == 2
    assert workspace_user.latest_required_legal_acceptance_at is not None
    assert UserLegalAcceptance.objects.filter(user=workspace_user).count() == 2


@pytest.mark.django_db
def test_record_attestation_persists_metadata(workspace_user):
    attestation = LegalAcceptanceService.record_attestation(
        user=workspace_user,
        kind=UserLegalAttestation.Kind.AI_OUTPUT_REVIEW,
        context="pytest",
        metadata={"source": "test"},
        ip_address="127.0.0.1",
        user_agent="pytest",
    )

    assert attestation.metadata == {"source": "test"}
    assert str(attestation) == f"{workspace_user.pk}:ai-output-review:pytest"


@pytest.mark.django_db
def test_get_user_compliance_reflects_required_acceptance(
    workspace_user,
    legal_versions,
):
    before = LegalAcceptanceService.get_user_compliance(workspace_user)
    LegalAcceptanceService.accept_documents(
        user=workspace_user,
        document_keys=before["required_signup_documents"],
        source=UserLegalAcceptance.Source.SIGNUP,
    )
    after = LegalAcceptanceService.get_user_compliance(workspace_user)

    assert before["has_required_signup_acceptance"] is False
    assert after["has_required_signup_acceptance"] is True


@pytest.mark.django_db
def test_legal_admin_pages(admin_client):
    urls = [
        reverse("admin:legal_legaldocumentversion_changelist"),
        reverse("admin:legal_userlegalacceptance_changelist"),
        reverse("admin:legal_userlegalattestation_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK
