from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse

from talk2record.organizations.models import Membership
from talk2record.organizations.services import OrganizationAPIKeyService


@pytest.mark.django_db
def test_organization_and_membership_str(organization, workspace_user):
    membership = workspace_user.memberships.get()

    assert str(organization) == "Acme Workspace"
    assert str(membership) == f"{workspace_user.email} -> {organization.name}"


@pytest.mark.django_db
def test_membership_unique_constraint(user, organization):
    Membership.objects.create(user=user, organization=organization)

    with pytest.raises(IntegrityError):
        Membership.objects.create(user=user, organization=organization)


@pytest.mark.django_db
def test_organization_admin_pages(admin_client, workspace_user):
    org_url = reverse("admin:organizations_organization_changelist")
    membership_url = reverse("admin:organizations_membership_changelist")
    api_keys_url = reverse("admin:organizations_organizationapikey_changelist")

    org_response = admin_client.get(org_url)
    membership_response = admin_client.get(membership_url)
    api_keys_response = admin_client.get(api_keys_url)

    assert org_response.status_code == HTTPStatus.OK
    assert membership_response.status_code == HTTPStatus.OK
    assert api_keys_response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_organization_api_key_service_roundtrip(organization, workspace_user):
    api_key, raw_key = OrganizationAPIKeyService.create_key(
        organization=organization,
        name="Ingestion key",
        created_by=workspace_user,
    )
    resolved = OrganizationAPIKeyService.resolve_active_key(
        raw_key,
        required_scope="ingestion:write",
    )
    assert resolved is not None
    assert resolved.pk == api_key.pk
    OrganizationAPIKeyService.record_key_usage(
        api_key=resolved,
        ip_address="127.0.0.1",
        user_agent="pytest-client",
    )
    resolved.refresh_from_db()
    assert resolved.last_used_ip == "127.0.0.1"
