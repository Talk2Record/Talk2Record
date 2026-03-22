from http import HTTPStatus

import pytest
from django.urls import reverse
from django.db import IntegrityError

from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration
from talk2record.integrations.models import WhatsAppInboundRoute
from talk2record.integrations.services import get_active_integration
from talk2record.integrations.services import get_active_integration_secret


@pytest.mark.django_db
def test_integration_models_str(organization):
    integration = Integration.objects.create(slug="whatsapp", enabled=True, config={})
    credential = ApiCredential.objects.create(
        integration=integration,
        encrypted_secret="xyz",
    )
    route = WhatsAppInboundRoute.objects.create(
        phone_number_id="123456789",
        organization=organization,
    )

    assert str(integration) == "whatsapp"
    assert str(credential) == "whatsapp credential"
    assert str(route) == f"123456789 -> {organization.slug}"


def test_secret_vault_round_trip_and_mask():
    encrypted = SecretVault.encrypt("supersecret1234")

    assert SecretVault.decrypt(encrypted) == "supersecret1234"
    assert SecretVault.encrypt("") == ""
    assert SecretVault.decrypt("") == ""
    assert SecretVault.mask("supersecret1234") == "supe***1234"
    assert SecretVault.mask("short") == "****"


@pytest.mark.django_db
def test_integration_admin_pages(admin_client, integration, organization):
    ApiCredential.objects.create(
        integration=integration,
        encrypted_secret="xyz",
    )
    WhatsAppInboundRoute.objects.create(
        phone_number_id="123456789",
        organization=organization,
    )

    urls = [
        reverse("admin:integrations_integration_changelist"),
        reverse("admin:integrations_apicredential_changelist"),
        reverse("admin:integrations_whatsappinboundroute_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_get_active_integration_returns_none_when_missing_or_disabled():
    assert get_active_integration("whatsapp") is None
    Integration.objects.create(slug="whatsapp", enabled=False, config={})
    assert get_active_integration("whatsapp") is None


@pytest.mark.django_db
def test_get_active_integration_secret_reads_encrypted_credential():
    integration = Integration.objects.create(
        slug="ai",
        enabled=True,
        config={"provider": "mock"},
    )
    ApiCredential.objects.create(
        integration=integration,
        encrypted_secret=SecretVault.encrypt("ai-secret"),
    )

    assert get_active_integration_secret("ai") == "ai-secret"


@pytest.mark.django_db
def test_api_credential_is_unique_per_integration():
    integration = Integration.objects.create(slug="stripe", enabled=True, config={})
    ApiCredential.objects.create(
        integration=integration,
        encrypted_secret=SecretVault.encrypt("one"),
    )

    with pytest.raises(IntegrityError):
        ApiCredential.objects.create(
            integration=integration,
            encrypted_secret=SecretVault.encrypt("two"),
        )
