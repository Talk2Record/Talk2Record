from __future__ import annotations

import pytest
from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import RefreshToken

from talk2record.notifications.consumers import NotificationConsumer


def _make_token(user) -> str:
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_notification_consumer_connects_with_valid_token(workspace_user):
    token = await sync_to_async(_make_token)(workspace_user)

    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        f"/ws/notifications/?token={token}",
    )
    communicator.scope["type"] = "websocket"
    connected, _ = await communicator.connect()
    assert connected
    await communicator.disconnect()


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_notification_consumer_rejects_without_token(workspace_user):
    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        "/ws/notifications/",
    )
    communicator.scope["type"] = "websocket"
    connected, code = await communicator.connect()
    assert not connected
    assert code == 4001


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_notification_consumer_rejects_invalid_token(workspace_user):
    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        "/ws/notifications/?token=not-a-valid-jwt",
    )
    communicator.scope["type"] = "websocket"
    connected, code = await communicator.connect()
    assert not connected
    assert code == 4001


@pytest.mark.anyio
@pytest.mark.django_db(transaction=True)
async def test_notification_consumer_receives_notification_message(workspace_user):
    token = await sync_to_async(_make_token)(workspace_user)

    communicator = WebsocketCommunicator(
        NotificationConsumer.as_asgi(),
        f"/ws/notifications/?token={token}",
    )
    communicator.scope["type"] = "websocket"
    connected, _ = await communicator.connect()
    assert connected

    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()
    group_name = f"user_{workspace_user.id}"
    await channel_layer.group_send(
        group_name,
        {
            "type": "notification_message",
            "data": {"title": "Test", "message": "Hello"},
        },
    )

    response = await communicator.receive_json_from(timeout=3)
    assert response["title"] == "Test"
    assert response["message"] == "Hello"
    await communicator.disconnect()
