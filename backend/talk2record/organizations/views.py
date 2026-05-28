from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.viewsets import ViewSet

from talk2record.audit.models import AuditLog
from talk2record.audit.services import AuditService
from talk2record.organizations.invitations import InvitationError
from talk2record.organizations.invitations import MembershipInvitationService
from talk2record.organizations.invitations import build_invitation_accept_url
from talk2record.organizations.models import Membership
from talk2record.organizations.models import MembershipInvitation
from talk2record.organizations.models import Organization
from talk2record.organizations.models import OrganizationAPIKey
from talk2record.organizations.serializers import AcceptInvitationSerializer
from talk2record.organizations.serializers import APIKeyAuditEventSerializer
from talk2record.organizations.serializers import ChangeMembershipRoleSerializer
from talk2record.organizations.serializers import CreateOrganizationAPIKeySerializer
from talk2record.organizations.serializers import InviteMembershipSerializer
from talk2record.organizations.serializers import MembershipInvitationSerializer
from talk2record.organizations.serializers import MembershipSerializer
from talk2record.organizations.serializers import OrganizationAPIKeySerializer
from talk2record.organizations.serializers import OrganizationSerializer
from talk2record.organizations.services import OrganizationAPIKeyService
from talk2record.organizations.services import OrganizationContextService


class OrganizationViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationSerializer

    def get_queryset(self):
        return Organization.objects.filter(
            memberships__user=self.request.user,
        ).distinct()


class MembershipViewSet(ViewSet):
    """Team management endpoints for an authenticated user's organization."""

    permission_classes = [IsAuthenticated]

    def _resolved_context(self):
        return OrganizationContextService.resolve_user_context(self.request.user)

    def _ensure_admin(self):
        context = self._resolved_context()
        if context is None:
            return None, Response(
                {"detail": "Organization membership required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if context.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}:
            return None, Response(
                {"detail": "Only organization admins can manage team members."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return context, None

    def list(self, request):
        context = self._resolved_context()
        if context is None:
            return Response([], status=status.HTTP_200_OK)
        queryset = (
            Membership.objects.filter(organization=context.organization)
            .select_related("organization", "user")
            .order_by("joined_at")
        )
        return Response(
            MembershipSerializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk: str | None = None):
        context = self._resolved_context()
        if context is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        membership = get_object_or_404(
            Membership.objects.select_related("organization", "user"),
            pk=pk,
            organization=context.organization,
        )
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get", "post"], url_path="invitations")
    def invitations(self, request):
        context, denial = self._ensure_admin()
        if denial is not None:
            return denial

        if request.method == "GET":
            queryset = MembershipInvitation.objects.filter(
                organization=context.organization,
            ).select_related("organization", "invited_by")
            status_filter = request.query_params.get("status")
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            return Response(
                MembershipInvitationSerializer(queryset, many=True).data,
                status=status.HTTP_200_OK,
            )

        serializer = InviteMembershipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            created = MembershipInvitationService.create(
                organization=context.organization,
                email=serializer.validated_data["email"],
                role=serializer.validated_data["role"],
                invited_by=request.user,
            )
        except InvitationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        AuditService.log(
            action="membership.invited",
            resource_type="membership_invitation",
            resource_id=str(created.invitation.pk),
            actor=request.user,
            organization=context.organization,
            metadata={
                "email": created.invitation.email,
                "role": created.invitation.role,
            },
        )
        return Response(
            {
                "invitation": MembershipInvitationSerializer(created.invitation).data,
                "acceptUrl": build_invitation_accept_url(created.raw_token),
                # Return the raw token only at creation time.
                "token": created.raw_token,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path=r"invitations/(?P<invitation_id>\d+)/revoke",
    )
    def revoke_invitation(self, request, invitation_id: str | None = None):
        context, denial = self._ensure_admin()
        if denial is not None:
            return denial
        invitation = get_object_or_404(
            MembershipInvitation,
            pk=invitation_id,
            organization=context.organization,
        )
        try:
            MembershipInvitationService.revoke(
                invitation=invitation,
                actor=request.user,
            )
        except InvitationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        AuditService.log(
            action="membership.invite_revoked",
            resource_type="membership_invitation",
            resource_id=str(invitation.pk),
            actor=request.user,
            organization=context.organization,
            metadata={"email": invitation.email},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["patch"], url_path="role")
    def change_role(self, request, pk: str | None = None):
        context, denial = self._ensure_admin()
        if denial is not None:
            return denial
        membership = get_object_or_404(
            Membership,
            pk=pk,
            organization=context.organization,
        )
        serializer = ChangeMembershipRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            MembershipInvitationService.change_role(
                membership=membership,
                new_role=serializer.validated_data["role"],
                actor=request.user,
            )
        except InvitationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        AuditService.log(
            action="membership.role_changed",
            resource_type="membership",
            resource_id=str(membership.pk),
            actor=request.user,
            organization=context.organization,
            metadata={"role": membership.role},
        )
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, pk: str | None = None):
        context, denial = self._ensure_admin()
        if denial is not None:
            return denial
        membership = get_object_or_404(
            Membership,
            pk=pk,
            organization=context.organization,
        )
        try:
            MembershipInvitationService.remove(
                membership=membership,
                actor=request.user,
            )
        except InvitationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        AuditService.log(
            action="membership.removed",
            resource_type="membership",
            resource_id=str(membership.pk),
            actor=request.user,
            organization=context.organization,
            metadata={"email": membership.user.email},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        queryset = Membership.objects.filter(user=request.user).select_related(
            "organization",
        )
        return Response(
            MembershipSerializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )


class AcceptInvitationView(APIView):
    """Accept an invitation token. Authenticated so we can bind to the current user."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            membership = MembershipInvitationService.accept(
                raw_token=serializer.validated_data["token"],
                user=request.user,
            )
        except InvitationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )


class InvitationLookupView(APIView):
    """Look up invitation details by token (unauthenticated).

    Used by the frontend accept page to show ``organization name``, ``role``,
    and ``email`` before the user logs in / registers.
    """

    permission_classes = [AllowAny]

    def get(self, request, token: str):
        invitation = MembershipInvitationService.find_by_token(token)
        if invitation is None:
            return Response(
                {"detail": "Invitation not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "organization": OrganizationSerializer(invitation.organization).data,
                "email": invitation.email,
                "role": invitation.role,
                "status": invitation.status,
                "expiresAt": invitation.expires_at,
            },
            status=status.HTTP_200_OK,
        )


class OrganizationAPIKeyViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def _resolved_context(self):
        return OrganizationContextService.resolve_user_context(self.request.user)

    def _log_api_key_audit(
        self,
        *,
        action: str,
        organization,
        api_key: OrganizationAPIKey,
        metadata: dict[str, object] | None = None,
    ) -> None:
        AuditService.log(
            action=action,
            resource_type="organization_api_key",
            resource_id=str(api_key.pk),
            actor=self.request.user,
            organization=organization,
            metadata=metadata or {},
        )

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
        include_inactive = request.query_params.get("includeInactive", "").lower() in {
            "1",
            "true",
            "yes",
        }
        queryset = OrganizationAPIKey.objects.filter(
            organization=context.organization,
        )
        if not include_inactive:
            queryset = queryset.filter(is_active=True)
        queryset = queryset.order_by("created_at")
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
        scope_preset = serializer.validated_data.get("scopePreset")
        rate_limit_per_minute = serializer.validated_data.get("rateLimitPerMinute")
        api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=context.organization,
            name=serializer.validated_data["name"],
            scopes=scopes,
            scope_preset=scope_preset,
            rate_limit_per_minute=rate_limit_per_minute,
            created_by=request.user,
            expires_in_days=expires_in_days,
        )
        self._log_api_key_audit(
            action="organization.api_key.created",
            organization=context.organization,
            api_key=api_key,
            metadata={"scopes": list(api_key.scopes)},
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
        self._log_api_key_audit(
            action="organization.api_key.revoked",
            organization=context.organization,
            api_key=api_key,
        )
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
        self._log_api_key_audit(
            action="organization.api_key.rotated",
            organization=context.organization,
            api_key=api_key,
            metadata={"replacement_key_id": replacement.pk},
        )
        return Response(
            {
                "apiKey": raw_key,
                "key": OrganizationAPIKeySerializer(replacement).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path="audit-events")
    def audit_events(self, request, pk: str | None = None):
        context, denial = self._ensure_can_manage_keys()
        if denial is not None:
            return denial
        get_object_or_404(
            OrganizationAPIKey,
            pk=pk,
            organization=context.organization,
        )
        events = AuditLog.objects.filter(
            organization=context.organization,
            resource_type="organization_api_key",
            resource_id=str(pk),
        ).order_by("-created_at")
        serializer = APIKeyAuditEventSerializer(events, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
