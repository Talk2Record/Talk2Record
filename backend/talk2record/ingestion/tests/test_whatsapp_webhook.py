from __future__ import annotations

import pytest
from talk2record.organizations.models import Organization
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.ingestion.models import WhatsAppRawPayload
from talk2record.records.models import Record
from talk2record.whatsapp.models import WhatsAppSettings


@pytest.mark.django_db
class TestWhatsAppWebhook:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    @pytest.fixture
    def webhook_payload(self) -> dict:
        return {
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "123456789"},
                                "messages": [
                                    {
                                        "id": "wamid.ABCD123",
                                        "from": "254700000001",
                                        "audio": {
                                            "id": "media-id-abcd123",
                                            "mime_type": "audio/ogg; codecs=opus",
                                            "sha256": "abc123",
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        }

    def test_verification_success(self, integration, api_client: APIClient):
        integration.enabled = True
        integration.config = {"verify_token": "verify-me"}
        integration.save(update_fields=["enabled", "config", "updated_at"])
        response = api_client.get(
            reverse("api-whatsapp-webhook"),
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "verify-me",
                "hub.challenge": "challenge-token",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.content.decode() == "challenge-token"

    def test_verification_rejects_invalid_token(self, integration, api_client: APIClient):
        integration.enabled = True
        integration.config = {"verify_token": "expected-token"}
        integration.save(update_fields=["enabled", "config", "updated_at"])
        response = api_client.get(
            reverse("api-whatsapp-webhook"),
            {
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "challenge-token",
            },
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_post_creates_payload_and_record(
        self,
        monkeypatch: pytest.MonkeyPatch,
        integration,
        api_credential,
        whatsapp_route,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        integration.config = {"verify_token": "verify-me"}
        integration.enabled = True
        integration.save(update_fields=["config", "enabled", "updated_at"])
        api_credential.encrypted_credential = ""
        api_credential.save(update_fields=["encrypted_credential", "updated_at"])

        queued: list[tuple[int, int | None, str, str]] = []
        published_events: list[str] = []

        def fake_delay(record_id: int, payload_id: int | None = None, **kwargs):
            queued.append(
                (
                    record_id,
                    payload_id,
                    str(kwargs.get("request_id", "")),
                    str(kwargs.get("event_id", "")),
                ),
            )

        def fake_publish(event):
            published_events.append(event.name)

        monkeypatch.setattr(
            "talk2record.whatsapp.views.process_whatsapp_record.delay",
            fake_delay,
        )
        monkeypatch.setattr(
            "talk2record.whatsapp.views.publish_after_commit",
            fake_publish,
        )

        response = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
            HTTP_X_REQUEST_ID="req-test-1",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["accepted"] == 1
        assert response.data["duplicates"] == 0
        assert (
            WhatsAppRawPayload.objects.filter(message_id="wamid.ABCD123").count() == 1
        )
        record = Record.objects.get(
            source=Record.Source.WHATSAPP,
            source_reference="wamid.ABCD123",
        )
        assert record.organization_id == whatsapp_route.organization_id
        assert record.media_id == "media-id-abcd123"
        raw = WhatsAppRawPayload.objects.get(message_id="wamid.ABCD123")
        assert raw.media_id == "media-id-abcd123"
        assert queued == [
            (
                record.pk,
                raw.pk,
                "req-test-1",
                queued[0][3],
            ),
        ]
        assert queued[0][3]
        assert response["X-Request-ID"] == "req-test-1"
        assert "record.created" in published_events
        assert "ingestion.received" in published_events

    def test_post_is_idempotent(
        self,
        monkeypatch: pytest.MonkeyPatch,
        integration,
        api_credential,
        whatsapp_route,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        integration.enabled = True
        integration.save(update_fields=["enabled", "updated_at"])
        api_credential.encrypted_credential = ""
        api_credential.save(update_fields=["encrypted_credential", "updated_at"])
        assert whatsapp_route.phone_number_id == "123456789"
        monkeypatch.setattr(
            "talk2record.whatsapp.views.process_whatsapp_record.delay",
            lambda *args, **kwargs: None,
        )

        first = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
        )
        second = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
        )

        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_200_OK
        assert (
            Record.objects.filter(
                source_reference="wamid.ABCD123",
                source=Record.Source.WHATSAPP,
            ).count()
            == 1
        )
        assert (
            WhatsAppRawPayload.objects.filter(message_id="wamid.ABCD123").count() == 1
        )
        assert second.data["accepted"] == 0
        assert second.data["duplicates"] == 1

    def test_post_respects_daily_quota(
        self,
        settings,
        monkeypatch: pytest.MonkeyPatch,
        integration,
        api_credential,
        whatsapp_route,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        settings.INGESTION_DAILY_RECORD_LIMIT_PER_ORG = 1
        integration.enabled = True
        integration.save(update_fields=["enabled", "updated_at"])
        api_credential.encrypted_credential = ""
        api_credential.save(update_fields=["encrypted_credential", "updated_at"])
        assert whatsapp_route.phone_number_id == "123456789"
        monkeypatch.setattr(
            "talk2record.whatsapp.views.process_whatsapp_record.delay",
            lambda *args, **kwargs: None,
        )

        first = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
        )
        second_payload = {
            **webhook_payload,
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "123456789"},
                                "messages": [
                                    {
                                        "id": "wamid.ABCD124",
                                        "from": "254700000002",
                                        "audio": {
                                            "id": "media-id-abcd124",
                                            "mime_type": "audio/ogg; codecs=opus",
                                        },
                                    },
                                ],
                            },
                        },
                    ],
                },
            ],
        }
        second = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=second_payload,
            format="json",
        )

        assert first.status_code == status.HTTP_200_OK
        assert second.status_code == status.HTTP_200_OK
        assert first.data["accepted"] == 1
        assert second.data["accepted"] == 0

    def test_post_ignores_when_whatsapp_inactive(
        self,
        db,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        s = WhatsAppSettings.get_solo()
        s.enabled = False
        s.save(update_fields=["enabled", "updated_at"])
        response = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ignored"
        assert response.data["accepted"] == 0

    def test_post_routes_by_phone_number_id(
        self,
        monkeypatch: pytest.MonkeyPatch,
        integration,
        api_credential,
        whatsapp_route,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        integration.enabled = True
        integration.save(update_fields=["enabled", "updated_at"])
        api_credential.encrypted_credential = ""
        api_credential.save(update_fields=["encrypted_credential", "updated_at"])
        secondary_org = Organization.objects.create(name="Secondary Org", slug="secondary-org")
        whatsapp_route.phone_number_id = "route-a"
        whatsapp_route.save(update_fields=["phone_number_id", "updated_at"])
        whatsapp_route.__class__.objects.create(
            organization=secondary_org,
            phone_number_id="route-b",
        )
        payload = {
            **webhook_payload,
            "entry": [
                {
                    "changes": [
                        {
                            "value": {
                                "metadata": {"phone_number_id": "route-b"},
                                "messages": webhook_payload["entry"][0]["changes"][0]["value"]["messages"],
                            },
                        },
                    ],
                },
            ],
        }
        monkeypatch.setattr(
            "talk2record.whatsapp.views.process_whatsapp_record.delay",
            lambda *args, **kwargs: None,
        )

        response = api_client.post(reverse("api-whatsapp-webhook"), data=payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        record = Record.objects.get(source_reference="wamid.ABCD123")
        assert record.organization_id == secondary_org.id

    def test_post_ignores_when_integration_disabled(
        self,
        integration,
        api_client: APIClient,
        webhook_payload: dict,
    ):
        integration.enabled = False
        integration.save(update_fields=["enabled", "updated_at"])
        response = api_client.post(
            reverse("api-whatsapp-webhook"),
            data=webhook_payload,
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ignored"
        assert response.data["accepted"] == 0
