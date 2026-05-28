from __future__ import annotations

import pytest

from talk2record.organizations.models import Organization
from talk2record.whatsapp.models import WhatsAppAccount
from talk2record.whatsapp.models import WhatsAppConversation
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppMessage
from talk2record.whatsapp.services.inbound import WhatsAppInboundService


def _audio_payload(
    *,
    phone_number_id: str = "123456789",
    wa_message_id: str = "wamid.AUDIO",
    sender: str = "254700000001",
    display_number: str = "+254700000099",
) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {
                                "phone_number_id": phone_number_id,
                                "display_phone_number": display_number,
                            },
                            "contacts": [
                                {"wa_id": sender, "profile": {"name": "Alice"}},
                            ],
                            "messages": [
                                {
                                    "id": wa_message_id,
                                    "from": sender,
                                    "timestamp": "1700000000",
                                    "type": "audio",
                                    "audio": {
                                        "id": "media-123",
                                        "mime_type": "audio/ogg; codecs=opus",
                                        "sha256": "deadbeef",
                                    },
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }


def _text_payload(
    *,
    phone_number_id: str = "123456789",
    wa_message_id: str = "wamid.TEXT",
    sender: str = "254700000002",
    body: str = "Hello there",
) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": phone_number_id},
                            "messages": [
                                {
                                    "id": wa_message_id,
                                    "from": sender,
                                    "timestamp": "1700000100",
                                    "type": "text",
                                    "text": {"body": body},
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }


def _status_payload(
    *,
    phone_number_id: str,
    wa_message_id: str,
    new_status: str,
) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": phone_number_id},
                            "statuses": [
                                {
                                    "id": wa_message_id,
                                    "status": new_status,
                                    "timestamp": "1700000500",
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    }


@pytest.mark.django_db
class TestWhatsAppInboundService:
    def test_persists_account_conversation_message(self, organization: Organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="123456789",
        )

        result = WhatsAppInboundService.process_webhook(_audio_payload())
        assert len(result) == 1
        persisted = result[0]
        assert persisted.created is True

        account = WhatsAppAccount.objects.get(phone_number_id="123456789")
        assert account.organization_id == organization.pk
        assert account.display_number == "+254700000099"

        conversation = WhatsAppConversation.objects.get(
            account=account,
            contact_wa_id="254700000001",
        )
        assert conversation.contact_name == "Alice"
        assert conversation.last_message_at is not None
        assert conversation.last_inbound_at is not None

        message = WhatsAppMessage.objects.get(wa_message_id="wamid.AUDIO")
        assert message.direction == WhatsAppMessage.Direction.INBOUND
        assert message.message_type == WhatsAppMessage.MessageType.AUDIO
        assert message.media_id == "media-123"
        assert message.media_mime == "audio/ogg; codecs=opus"
        assert message.status == WhatsAppMessage.Status.RECEIVED

    def test_is_idempotent_for_duplicate_message(self, organization: Organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="123456789",
        )
        first = WhatsAppInboundService.process_webhook(_audio_payload())
        assert first[0].created is True
        second = WhatsAppInboundService.process_webhook(_audio_payload())
        assert second[0].created is False
        assert WhatsAppMessage.objects.filter(wa_message_id="wamid.AUDIO").count() == 1

    def test_skips_unmapped_phone_number(self, organization: Organization):
        result = WhatsAppInboundService.process_webhook(
            _audio_payload(phone_number_id="unmapped"),
        )
        assert result == []
        assert WhatsAppAccount.objects.count() == 0
        assert WhatsAppMessage.objects.count() == 0

    def test_records_text_message_with_body(self, organization: Organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="123456789",
        )
        WhatsAppInboundService.process_webhook(_text_payload(body="Hello there"))
        message = WhatsAppMessage.objects.get(wa_message_id="wamid.TEXT")
        assert message.message_type == WhatsAppMessage.MessageType.TEXT
        assert message.body == "Hello there"

    def test_applies_delivery_status_updates(self, organization: Organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="123456789",
        )
        WhatsAppInboundService.process_webhook(_audio_payload())
        WhatsAppInboundService.process_webhook(
            _status_payload(
                phone_number_id="123456789",
                wa_message_id="wamid.AUDIO",
                new_status="delivered",
            ),
        )
        message = WhatsAppMessage.objects.get(wa_message_id="wamid.AUDIO")
        assert message.status == WhatsAppMessage.Status.DELIVERED

    def test_failed_status_captures_error_details(self, organization: Organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="123456789",
        )
        WhatsAppInboundService.process_webhook(_audio_payload())

        payload = {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "123456789"},
                                "statuses": [
                                    {
                                        "id": "wamid.AUDIO",
                                        "status": "failed",
                                        "errors": [
                                            {
                                                "code": 131047,
                                                "title": "Re-engagement message",
                                                "message": "Outside 24h window",
                                            },
                                        ],
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        }
        WhatsAppInboundService.process_webhook(payload)
        message = WhatsAppMessage.objects.get(wa_message_id="wamid.AUDIO")
        assert message.status == WhatsAppMessage.Status.FAILED
        assert message.error_code == "131047"
        assert "Re-engagement" in message.error_message
