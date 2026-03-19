import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.organizations.models import Membership
from talk2record.organizations.models import OrganizationAPIKey


@pytest.mark.django_db
class TestOrganizationAPIKeyEndpoints:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_owner_can_create_list_and_revoke_key(
        self,
        api_client: APIClient,
        workspace_user,
    ):
        api_client.force_authenticate(user=workspace_user)
        create_response = api_client.post(
            reverse("api:organization-api-key-list"),
            data={
                "name": "Public ingestion",
                "scopes": ["ingestion:write"],
                "expiresInDays": 30,
            },
            format="json",
        )

        key_id = create_response.data["key"]["id"]
        list_response = api_client.get(reverse("api:organization-api-key-list"))
        revoke_response = api_client.post(
            reverse("api:organization-api-key-revoke", kwargs={"pk": key_id}),
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        assert create_response.data["apiKey"].startswith("t2r_")
        assert create_response.data["key"]["expiresAt"] is not None
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data) == 1
        assert revoke_response.status_code == status.HTTP_204_NO_CONTENT
        api_key = OrganizationAPIKey.objects.get(pk=key_id)
        assert api_key.is_active is False
        assert api_key.revoked_at is not None

    def test_owner_can_rotate_key(self, api_client: APIClient, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        create_response = api_client.post(
            reverse("api:organization-api-key-list"),
            data={"name": "Rotatable key", "scopes": ["ingestion:write"]},
            format="json",
        )
        source_key_id = create_response.data["key"]["id"]

        rotate_response = api_client.post(
            reverse("api:organization-api-key-rotate", kwargs={"pk": source_key_id}),
        )

        source_key = OrganizationAPIKey.objects.get(pk=source_key_id)
        replacement_key = OrganizationAPIKey.objects.get(pk=rotate_response.data["key"]["id"])
        assert rotate_response.status_code == status.HTTP_201_CREATED
        assert rotate_response.data["apiKey"].startswith("t2r_")
        assert replacement_key.is_active is True
        assert source_key.is_active is False
        assert source_key.revoked_at is not None

    def test_operator_cannot_manage_api_keys(
        self,
        api_client: APIClient,
        user,
        organization,
    ):
        Membership.objects.create(
            user=user,
            organization=organization,
            role=Membership.Role.OPERATOR,
        )
        user.current_organization = organization
        user.save(update_fields=["current_organization"])
        api_client.force_authenticate(user=user)

        create_response = api_client.post(
            reverse("api:organization-api-key-list"),
            data={"name": "Denied key"},
            format="json",
        )
        list_response = api_client.get(reverse("api:organization-api-key-list"))

        assert create_response.status_code == status.HTTP_403_FORBIDDEN
        assert list_response.status_code == status.HTTP_403_FORBIDDEN
