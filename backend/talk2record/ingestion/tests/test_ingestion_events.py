from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import INGESTION_RECEIVED
from talk2record.events.names import RECORD_CREATED


@pytest.mark.django_db(transaction=True)
def test_whatsapp_webhook_emits_record_created_and_ingestion_received_events(
    settings,
    integration,
    api_credential,
    whatsapp_route,
    organization,
):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    api_credential.encrypted_secret = ""
    api_credential.save(update_fields=["encrypted_secret", "updated_at"])

    webhook_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "123456789"},
                            "messages": [
                                {
                                    "id": "wamid.ingestion-events-test-001",
                                    "from": "254712345678",
                                    "audio": {
                                        "id": "media-id-events-test-001",
                                        "mime_type": "audio/ogg; codecs=opus",
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }

    client = APIClient()
    response = client.post(
        reverse("api-whatsapp-webhook"),
        data=webhook_payload,
        format="json",
    )

    assert response.status_code == 200
    assert DomainEventRecord.objects.filter(name=RECORD_CREATED).exists()
    assert DomainEventRecord.objects.filter(name=INGESTION_RECEIVED).exists()
