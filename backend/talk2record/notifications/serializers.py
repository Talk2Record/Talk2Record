from rest_framework import serializers

from talk2record.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer[Notification]):
    class Meta:
        model = Notification
        fields = [
            "id",
            "type",
            "title",
            "message",
            "link_url",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields
