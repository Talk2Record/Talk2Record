from http import HTTPStatus

import pytest
from django.urls import reverse

from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential


@pytest.mark.django_db
def test_integration_models_str(integration, organization_integration):
    credential = ApiCredential.objects.create(
        organization_integration=organization_integration,
        label="Primary key",
        encrypted_api_key="abc",
        encrypted_secret="xyz",
    )

    assert str(integration) == "WhatsApp"
    assert str(organization_integration) == f"{organization_integration.organization.name}: WhatsApp"
    assert str(credential) == f"{organization_integration}: Primary key"


def test_secret_vault_round_trip_and_mask():
    encrypted = SecretVault.encrypt("supersecret1234")

    assert SecretVault.decrypt(encrypted) == "supersecret1234"
    assert SecretVault.encrypt("") == ""
    assert SecretVault.decrypt("") == ""
    assert SecretVault.mask("supersecret1234") == "supe***1234"
    assert SecretVault.mask("short") == "****"


@pytest.mark.django_db
def test_integration_admin_pages(admin_client, organization_integration):
    ApiCredential.objects.create(
        organization_integration=organization_integration,
        label="Primary key",
        encrypted_api_key="abc",
        encrypted_secret="xyz",
    )

    urls = [
        reverse("admin:integrations_integration_changelist"),
        reverse("admin:integrations_organizationintegration_changelist"),
        reverse("admin:integrations_apicredential_changelist"),
    ]

    for url in urls:
        response = admin_client.get(url)
        assert response.status_code == HTTPStatus.OK
