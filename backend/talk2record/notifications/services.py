from __future__ import annotations

from typing import TYPE_CHECKING

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from talk2record.notifications.models import Notification
from talk2record.notifications.serializers import NotificationSerializer
from talk2record.organizations.models import Membership

if TYPE_CHECKING:
    from talk2record.users.models import User


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
    def create(  # noqa: PLR0913
        user: User,
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

    @staticmethod
    def broadcast_record_event(
        *,
        organization,
        record_id: int,
        status: str,
        event_type: str,
        summary: str = "",
    ) -> None:
        payload = {
            "eventType": event_type,
            "record_id": record_id,
            "status": status,
            "summary": summary,
        }
        memberships = organization.memberships.filter(
            status=Membership.Status.ACTIVE,
        ).select_related("user")
        for membership in memberships:
            _send_notification_to_user(membership.user_id, payload)
