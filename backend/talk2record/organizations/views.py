from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.organizations.serializers import MembershipSerializer
from talk2record.organizations.serializers import OrganizationSerializer


class OrganizationViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(memberships__user=self.request.user).distinct()


class MembershipViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MembershipSerializer

    def get_queryset(self):
        return Membership.objects.filter(user=self.request.user).select_related("organization")
