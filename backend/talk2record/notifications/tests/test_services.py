from __future__ import annotations

from unittest.mock import patch

import pytest
from django.utils import timezone

from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService


@pytest.mark.django_db
def test_notification_service_create(workspace_user, organization):
    with patch("talk2record.notifications.services._send_notification_to_user"):
        notification = NotificationService.create(
            user=workspace_user,
            notification_type=Notification.Type.RECORD_STORED,
            title="Record stored",
            message="Your record is ready.",
            link_url="/dashboard/records",
            organization=organization,
            metadata={"record_id": 1},
        )

    assert notification.pk is not None
    assert notification.user == workspace_user
    assert notification.organization == organization
    assert notification.type == Notification.Type.RECORD_STORED
    assert notification.title == "Record stored"
    assert notification.message == "Your record is ready."
    assert notification.metadata == {"record_id": 1}


@pytest.mark.django_db
def test_notification_service_create_sends_websocket(workspace_user, organization):
    sent: list[int] = []

    def fake_send(user_id, _data):
        sent.append(user_id)

    with patch("talk2record.notifications.services._send_notification_to_user", fake_send):
        NotificationService.create(
            user=workspace_user,
            notification_type=Notification.Type.GENERAL,
            title="Hello",
            organization=organization,
        )

    assert workspace_user.id in sent


@pytest.mark.django_db
def test_notification_service_broadcast_record_event(workspace_user, organization):
    sent_payloads: list[tuple[int, dict]] = []

    def fake_send(user_id, payload):
        sent_payloads.append((user_id, payload))

    with patch("talk2record.notifications.services._send_notification_to_user", fake_send):
        NotificationService.broadcast_record_event(
            organization=organization,
            record_id=42,
            status="stored",
            event_type="record_updated",
            summary="Done",
        )

    assert any(user_id == workspace_user.id for user_id, _ in sent_payloads)
    payloads = [p for _, p in sent_payloads]
    assert any(p["record_id"] == 42 for p in payloads)
    assert any(p["eventType"] == "record_updated" for p in payloads)


@pytest.mark.django_db
def test_notification_service_mark_all_read(workspace_user):
    with patch("talk2record.notifications.services._send_notification_to_user"):
        for i in range(3):
            NotificationService.create(
                user=workspace_user,
                notification_type=Notification.Type.GENERAL,
                title=f"Notification {i}",
            )

    updated = Notification.objects.filter(
        user=workspace_user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())

    assert updated == 3
    assert Notification.objects.filter(user=workspace_user, read_at__isnull=True).count() == 0
