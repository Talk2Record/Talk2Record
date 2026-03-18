"""
WebSocket URL routing for Django Channels.
"""

from django.urls import path

from talk2record.notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
