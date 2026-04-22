from __future__ import annotations

from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.organizations.models import Membership, Organization
from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory
from talk2record.whatsapp.models import (
    WhatsAppAccount,
    WhatsAppConversation,
    WhatsAppInboundRoute,
    WhatsAppMessage,
    WhatsAppSettings,
)
from talk2record.whatsapp.services.inbound import WhatsAppInboundService


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def seeded_messages(organization: Organization):
    WhatsAppInboundRoute.objects.create(
        organization=organization,
        phone_number_id="123456789",
    )
    payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "123456789"},
                            "messages": [
                                {
                                    "id": "wamid.TEST1",
                                    "from": "254700000001",
                                    "type": "text",
                                    "text": {"body": "Hi"},
                                    "timestamp": "1700000000",
                                }
                            ],
                        }
                    }
                ]
            }
        ]
    }
    WhatsAppInboundService.process_webhook(payload)
    return {
        "account": WhatsAppAccount.objects.get(phone_number_id="123456789"),
        "conversation": WhatsAppConversation.objects.get(contact_wa_id="254700000001"),
        "message": WhatsAppMessage.objects.get(wa_message_id="wamid.TEST1"),
    }


@pytest.mark.django_db
class TestWhatsAppReadOnlyViewSets:
    def test_member_can_list_conversations(
        self,
        api_client: APIClient,
        workspace_user: User,
        seeded_messages,
    ):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(reverse("api:whatsapp-conversation-list"))
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get("results", [])
        assert len(data) == 1

    def test_member_can_list_messages(
        self,
        api_client: APIClient,
        workspace_user: User,
        seeded_messages,
    ):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(reverse("api:whatsapp-message-list"))
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data.get("results", [])
        assert len(data) == 1
        assert data[0]["wa_message_id"] == "wamid.TEST1"

    def test_unauthenticated_gets_401(self, api_client: APIClient):
        response = api_client.get(reverse("api:whatsapp-message-list"))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_member_gets_empty(
        self,
        api_client: APIClient,
        seeded_messages,
    ):
        outsider = UserFactory.create()
        api_client.force_authenticate(user=outsider)
        response = api_client.get(reverse("api:whatsapp-message-list"))
        # IsOrgMember denies access for users without any membership.
        assert response.status_code in {
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
        }
        if response.status_code == status.HTTP_200_OK:
            data = (
                response.data
                if isinstance(response.data, list)
                else response.data.get("results", [])
            )
            assert data == []


@pytest.mark.django_db
class TestWhatsAppOutboundAPI:
    @pytest.fixture
    def _with_account(
        self,
        organization: Organization,
        integration: WhatsAppSettings,
    ):
        return WhatsAppAccount.objects.create(
            phone_number_id="123456789",
            organization=organization,
            status=WhatsAppAccount.Status.ACTIVE,
        )

    def test_operator_cannot_send(
        self,
        api_client: APIClient,
        organization: Organization,
        _with_account,
    ):
        operator = UserFactory.create(email="op@example.com")
        Membership.objects.create(
            user=operator,
            organization=organization,
            role=Membership.Role.OPERATOR,
            status=Membership.Status.ACTIVE,
        )
        operator.current_organization = organization
        operator.save(update_fields=["current_organization"])
        api_client.force_authenticate(user=operator)

        response = api_client.post(
            reverse("api:whatsapp-send-send"),
            data={"to": "254700000001", "type": "text", "body": "hi"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_send_text(
        self,
        api_client: APIClient,
        workspace_user: User,
        _with_account,
    ):
        api_client.force_authenticate(user=workspace_user)
        fake_response = {"messages": [{"id": "wamid.APIOUT"}]}
        with patch(
            "talk2record.whatsapp.services.outbound.WhatsAppCloudClient.send_message",
            return_value=fake_response,
        ):
            response = api_client.post(
                reverse("api:whatsapp-send-send"),
                data={"to": "254700000001", "type": "text", "body": "hello"},
                format="json",
            )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["message"]["wa_message_id"] == "wamid.APIOUT"
