from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.notifications.models import Notification
from talk2record.notifications.serializers import NotificationSerializer


class NotificationViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        qs = Notification.objects.filter(user=self.request.user)
        if self.request.query_params.get("unread_only", "").lower() in (
            "true",
            "1",
            "yes",
        ):
            qs = qs.filter(read_at__isnull=True)
        return qs.select_related("organization").order_by("-created_at")

    @action(detail=True, methods=["post", "patch"])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.read_at is None:
            from django.utils import timezone

            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)

    @action(detail=False, methods=["post"])
    def mark_all_read(self, request):
        from django.utils import timezone

        updated = Notification.objects.filter(
            user=request.user,
            read_at__isnull=True,
        ).update(read_at=timezone.now())
        return Response({"marked_count": updated}, status=status.HTTP_200_OK)
