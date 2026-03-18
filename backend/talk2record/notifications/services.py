from __future__ import annotations

from asgiref.sync import async_to_sync
from django.conf import settings
from channels.layers import get_channel_layer

from talk2record.notifications.models import Notification
from talk2record.notifications.serializers import NotificationSerializer


def _send_notification_to_user(user_id: int, notification_data: dict) -> None:
    """Send notification payload to user's WebSocket group."""
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    group_name = f"user_{user_id}"
    async_to_sync(channel_layer.group_send)(
        group_name,
        {"type": "notification_message", "data": notification_data},
    )


class NotificationService:
    @staticmethod
    def create(
        user: settings.AUTH_USER_MODEL,
        notification_type: str,
        title: str,
        message: str = "",
        link_url: str = "",
        organization=None,
        metadata: dict | None = None,
    ) -> Notification:
        notification = Notification.objects.create(
            user=user,
            organization=organization,
            type=notification_type,
            title=title,
            message=message,
            link_url=link_url or "",
            metadata=metadata or {},
        )
        data = NotificationSerializer(notification).data
        _send_notification_to_user(user.id, data)
        return notification
