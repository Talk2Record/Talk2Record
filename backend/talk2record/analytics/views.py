from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.serializers import DailyMetricSerializer


class DailyMetricViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyMetricSerializer

    def get_queryset(self):
        return DailyMetric.objects.filter(
            organization__memberships__user=self.request.user,
        ).select_related("organization")
