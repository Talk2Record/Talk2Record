from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from talk2record.records.models import Record
from talk2record.records.serializers import RecordSerializer


class RecordViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = RecordSerializer

    def get_queryset(self):
        return Record.objects.filter(
            organization__memberships__user=self.request.user,
        ).select_related("organization", "created_by")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
