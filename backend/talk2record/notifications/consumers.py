"""
WebSocket consumer for real-time notifications.
"""

from urllib.parse import parse_qs

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Consumer that sends notifications to authenticated users via WebSocket."""

    async def connect(self):
        """Authenticate via JWT in query string and join user's notification group."""
        query_string = self.scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        token_list = params.get("token", [])

        if not token_list:
            await self.close(code=4001)
            return

        token = token_list[0]
        try:
            access = AccessToken(token)
            user_id = access["user_id"]
            self.scope["user"] = await self._get_user(user_id)
        except (InvalidToken, TokenError, KeyError, TypeError):
            await self.close(code=4001)
            return

        if self.scope["user"] is None:
            await self.close(code=4001)
            return

        self.group_name = f"user_{self.scope['user'].id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def _get_user(self, user_id):
        """Fetch user by ID (async-compatible)."""
        try:
            return await User.objects.aget(pk=user_id)
        except User.DoesNotExist:
            return None

    async def disconnect(self, close_code):
        """Leave the group on disconnect."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notification_message(self, event):
        """Receive notification from channel layer and send to WebSocket."""
        await self.send_json(event.get("data", {}))
