from __future__ import annotations

from unittest.mock import patch

import pytest

from talk2record.organizations.models import Organization
from talk2record.users.models import User
from talk2record.whatsapp.client import WhatsAppCloudClientError
from talk2record.whatsapp.models import (
    WhatsAppAccount,
    WhatsAppMessage,
    WhatsAppSettings,
)
from talk2record.whatsapp.services.outbound import (
    OutboundSendError,
    WhatsAppOutboundService,
)


@pytest.mark.django_db
class TestWhatsAppOutboundService:
    @pytest.fixture
    def account(self, organization: Organization) -> WhatsAppAccount:
        return WhatsAppAccount.objects.create(
            phone_number_id="123456789",
            organization=organization,
            status=WhatsAppAccount.Status.ACTIVE,
        )

    def test_refuses_when_credentials_missing(
        self,
        organization: Organization,
        workspace_user: User,
        account: WhatsAppAccount,
    ):
        WhatsAppSettings.objects.all().delete()
        with pytest.raises(OutboundSendError):
            WhatsAppOutboundService.send_text(
                organization=organization,
                to="254700000001",
                body="hello",
                sent_by=workspace_user,
            )

    def test_refuses_when_no_account(
        self,
        organization: Organization,
        workspace_user: User,
        integration: WhatsAppSettings,
    ):
        with pytest.raises(OutboundSendError):
            WhatsAppOutboundService.send_text(
                organization=organization,
                to="254700000001",
                body="hello",
                sent_by=workspace_user,
            )

    def test_sends_text_and_persists(
        self,
        organization: Organization,
        workspace_user: User,
        account: WhatsAppAccount,
        integration: WhatsAppSettings,
    ):
        fake_response = {"messages": [{"id": "wamid.OUT123"}]}
        with patch(
            "talk2record.whatsapp.services.outbound.WhatsAppCloudClient.send_message",
            return_value=fake_response,
        ):
            result = WhatsAppOutboundService.send_text(
                organization=organization,
                to="254700000001",
                body="hello there",
                sent_by=workspace_user,
            )

        assert result.message.wa_message_id == "wamid.OUT123"
        assert result.message.direction == WhatsAppMessage.Direction.OUTBOUND
        assert result.message.status == WhatsAppMessage.Status.SENT
        assert result.message.body == "hello there"

    def test_records_failure_and_raises(
        self,
        organization: Organization,
        workspace_user: User,
        account: WhatsAppAccount,
        integration: WhatsAppSettings,
    ):
        with patch(
            "talk2record.whatsapp.services.outbound.WhatsAppCloudClient.send_message",
            side_effect=WhatsAppCloudClientError("boom"),
        ):
            with pytest.raises(OutboundSendError):
                WhatsAppOutboundService.send_text(
                    organization=organization,
                    to="254700000001",
                    body="hi",
                    sent_by=workspace_user,
                )

        failure = WhatsAppMessage.objects.get(
            direction=WhatsAppMessage.Direction.OUTBOUND,
            status=WhatsAppMessage.Status.FAILED,
        )
        assert "boom" in failure.error_message
