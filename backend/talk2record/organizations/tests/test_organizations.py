from http import HTTPStatus

import pytest
from django.db import IntegrityError
from django.urls import reverse

from talk2record.organizations.models import Membership


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

    org_response = admin_client.get(org_url)
    membership_response = admin_client.get(membership_url)

    assert org_response.status_code == HTTPStatus.OK
    assert membership_response.status_code == HTTPStatus.OK
