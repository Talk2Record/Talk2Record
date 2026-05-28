from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.events.models import DomainEvent as DomainEventRecord
from talk2record.events.names import RECORD_STORED
from talk2record.notifications.models import Notification
from talk2record.records.models import Record


@pytest.mark.django_db(transaction=True)
def test_full_whatsapp_to_stored_notification_flow(
    settings,
    integration,
    api_credential,
    whatsapp_route,
    workspace_user,
    organization,
):
    """
    Full E2E: POST webhook → record created → processing pipeline →
    STORED → AuditLog + Analytics Event + Notification + DomainEvent persisted
    """
    settings.CELERY_TASK_ALWAYS_EAGER = True
    api_credential.encrypted_credential = ""
    api_credential.save(update_fields=["encrypted_credential", "updated_at"])

    webhook_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "123456789"},
                            "messages": [
                                {
                                    "id": "wamid.e2e-flow-test-001",
                                    "from": "254712345678",
                                    "audio": {
                                        "id": "media-id-e2e-001",
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

    client = APIClient()
    response = client.post(
        reverse("api-whatsapp-webhook"),
        data=webhook_payload,
        format="json",
    )

    assert response.status_code == 200
    assert response.data["accepted"] == 1

    record = Record.objects.filter(
        source=Record.Source.WHATSAPP,
        source_reference="wamid.e2e-flow-test-001",
    ).first()
    assert record is not None
    assert record.status == Record.Status.STORED

    assert AuditLog.objects.filter(
        action=RECORD_STORED,
        resource_type="record",
        resource_id=str(record.pk),
    ).exists()

    assert Event.objects.filter(name="record_stored").exists()

    assert Notification.objects.filter(
        organization=organization,
        type=Notification.Type.RECORD_STORED,
    ).exists()

    domain_event = DomainEventRecord.objects.filter(name=RECORD_STORED).first()
    assert domain_event is not None
    assert domain_event.processed is True
    assert str(domain_event.resource_id) == str(record.pk)
