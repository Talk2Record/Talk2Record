from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.viewsets import ViewSet

from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.organizations.models import OrganizationAPIKey
from talk2record.organizations.serializers import CreateOrganizationAPIKeySerializer
from talk2record.organizations.serializers import OrganizationAPIKeySerializer
from talk2record.organizations.serializers import MembershipSerializer
from talk2record.organizations.serializers import OrganizationSerializer
from talk2record.organizations.services import OrganizationAPIKeyService
from talk2record.organizations.services import OrganizationContextService


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


class OrganizationAPIKeyViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def _resolved_context(self):
        return OrganizationContextService.resolve_user_context(self.request.user)

    def _ensure_can_manage_keys(self):
        context = self._resolved_context()
        if context is None:
            return None, Response(
                {"detail": "Organization membership required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if context.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}:
            return None, Response(
                {"detail": "Only organization admins can manage API keys."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return context, None

    def list(self, request):
        context, denial = self._ensure_can_manage_keys()
        if denial is not None:
            return denial
        queryset = OrganizationAPIKey.objects.filter(
            organization=context.organization,
            is_active=True,
        ).order_by("created_at")
        serializer = OrganizationAPIKeySerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        context, denial = self._ensure_can_manage_keys()
        if denial is not None:
            return denial

        serializer = CreateOrganizationAPIKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scopes = serializer.validated_data.get("scopes")
        expires_in_days = serializer.validated_data.get("expiresInDays")
        api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=context.organization,
            name=serializer.validated_data["name"],
            scopes=scopes,
            created_by=request.user,
            expires_in_days=expires_in_days,
        )
        return Response(
            {
                "apiKey": raw_key,
                "key": OrganizationAPIKeySerializer(api_key).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="revoke")
    def revoke(self, request, pk: str | None = None):
        context, denial = self._ensure_can_manage_keys()
        if denial is not None:
            return denial
        api_key = get_object_or_404(
            OrganizationAPIKey,
            pk=pk,
            organization=context.organization,
        )
        OrganizationAPIKeyService.revoke_key(api_key)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="rotate")
    def rotate(self, request, pk: str | None = None):
        context, denial = self._ensure_can_manage_keys()
        if denial is not None:
            return denial
        api_key = get_object_or_404(
            OrganizationAPIKey,
            pk=pk,
            organization=context.organization,
            is_active=True,
        )
        replacement, raw_key = OrganizationAPIKeyService.rotate_key(
            api_key=api_key,
            rotated_by=request.user,
        )
        return Response(
            {
                "apiKey": raw_key,
                "key": OrganizationAPIKeySerializer(replacement).data,
            },
            status=status.HTTP_201_CREATED,
        )
