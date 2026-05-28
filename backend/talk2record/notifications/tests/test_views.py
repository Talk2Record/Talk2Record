from __future__ import annotations

from http import HTTPStatus
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient

from talk2record.notifications.models import Notification


@pytest.fixture
def auth_client(workspace_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(workspace_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def notification(workspace_user, organization):
    with patch("talk2record.notifications.services._send_notification_to_user"):
        return Notification.objects.create(
            user=workspace_user,
            organization=organization,
            type=Notification.Type.RECORD_STORED,
            title="Test notification",
            message="Ready",
        )


@pytest.mark.django_db
def test_notification_list_returns_user_notifications(auth_client, notification):
    response = auth_client.get("/api/notifications/")
    assert response.status_code == HTTPStatus.OK
    data = (
        response.data
        if isinstance(response.data, list)
        else response.data.get("results", response.data)
    )
    titles = [n["title"] for n in data]
    assert "Test notification" in titles


@pytest.mark.django_db
def test_notification_list_unread_only_filter(
    workspace_user,
    organization,
    auth_client,
):
    with patch("talk2record.notifications.services._send_notification_to_user"):
        Notification.objects.create(
            user=workspace_user,
            organization=organization,
            type=Notification.Type.GENERAL,
            title="Unread",
        )
        from django.utils import timezone

        Notification.objects.create(
            user=workspace_user,
            organization=organization,
            type=Notification.Type.GENERAL,
            title="Already read",
            read_at=timezone.now(),
        )

    response = auth_client.get("/api/notifications/?unread_only=true")
    assert response.status_code == HTTPStatus.OK
    data = (
        response.data
        if isinstance(response.data, list)
        else response.data.get("results", response.data)
    )
    titles = [n["title"] for n in data]
    assert "Unread" in titles
    assert "Already read" not in titles


@pytest.mark.django_db
def test_notification_mark_read(auth_client, notification):
    assert notification.read_at is None
    response = auth_client.post(f"/api/notifications/{notification.pk}/mark_read/")
    assert response.status_code == HTTPStatus.OK
    notification.refresh_from_db()
    assert notification.read_at is not None


@pytest.mark.django_db
def test_notification_mark_all_read(workspace_user, organization, auth_client):
    with patch("talk2record.notifications.services._send_notification_to_user"):
        for i in range(3):
            Notification.objects.create(
                user=workspace_user,
                organization=organization,
                type=Notification.Type.GENERAL,
                title=f"Notification {i}",
            )

    response = auth_client.post("/api/notifications/mark_all_read/")
    assert response.status_code == HTTPStatus.OK
    assert response.data["marked_count"] == 3
    assert (
        Notification.objects.filter(user=workspace_user, read_at__isnull=True).count()
        == 0
    )


@pytest.mark.django_db
def test_notification_list_requires_authentication():
    client = APIClient()
    response = client.get("/api/notifications/")
    assert response.status_code == HTTPStatus.UNAUTHORIZED
