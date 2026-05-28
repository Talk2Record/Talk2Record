"""Platform-staff-only user administration endpoints.

These back an admin-only area of the dashboard (``dashboard/admin/users``).
They are protected by :class:`IsPlatformStaff` so only ``is_staff`` /
``is_superuser`` users can access them.
"""

from __future__ import annotations

from datetime import timedelta

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.tokens import RefreshToken

from talk2record.audit.services import AuditService
from talk2record.events import DomainEvent
from talk2record.events import publish_after_commit
from talk2record.events.names import USER_IMPERSONATED
from talk2record.events.names import USER_REACTIVATED
from talk2record.events.names import USER_SUSPENDED
from talk2record.organizations.permissions import IsPlatformStaff
from talk2record.users.models import User


class AdminUserSerializer(drf_serializers.ModelSerializer[User]):
    organizationsCount = drf_serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "is_active",
            "is_staff",
            "is_superuser",
            "onboarding_completed",
            "suspended_at",
            "suspended_reason",
            "date_joined",
            "last_login",
            "organizationsCount",
        ]
        read_only_fields = [
            "id",
            "email",
            "date_joined",
            "last_login",
            "organizationsCount",
        ]

    def get_organizationsCount(self, obj: User) -> int:
        return obj.memberships.count()


class SuspendUserSerializer(drf_serializers.Serializer):
    reason = drf_serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )


class AdminUserViewSet(
    RetrieveModelMixin,
    ListModelMixin,
    UpdateModelMixin,
    GenericViewSet,
):
    permission_classes = [IsAuthenticated, IsPlatformStaff]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all().order_by("-date_joined")
    lookup_field = "pk"

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | Q(name__icontains=search),
            )
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter == "active":
            queryset = queryset.filter(is_active=True, suspended_at__isnull=True)
        elif status_filter == "suspended":
            queryset = queryset.filter(suspended_at__isnull=False)
        elif status_filter == "inactive":
            queryset = queryset.filter(is_active=False)
        return queryset

    @action(detail=True, methods=["post"], url_path="suspend")
    def suspend(self, request, pk: str | None = None):
        user = get_object_or_404(User, pk=pk)
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot suspend yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = SuspendUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        user.is_active = False
        user.suspended_at = timezone.now()
        user.suspended_reason = reason
        user.save(update_fields=["is_active", "suspended_at", "suspended_reason"])

        # Revoke all active sessions for this user by blacklisting every
        # outstanding refresh token.
        _revoke_all_sessions(user)

        AuditService.log(
            action="user.suspended",
            resource_type="user",
            resource_id=str(user.pk),
            actor=request.user,
            metadata={"reason": reason},
        )
        publish_after_commit(
            DomainEvent(
                name=USER_SUSPENDED,
                organization_id=None,
                user_id=request.user.pk,
                resource_type="user",
                resource_id=str(user.pk),
                metadata={"reason": reason},
            ),
        )
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="reactivate")
    def reactivate(self, request, pk: str | None = None):
        user = get_object_or_404(User, pk=pk)
        user.is_active = True
        user.suspended_at = None
        user.suspended_reason = ""
        user.save(update_fields=["is_active", "suspended_at", "suspended_reason"])
        AuditService.log(
            action="user.reactivated",
            resource_type="user",
            resource_id=str(user.pk),
            actor=request.user,
            metadata={},
        )
        publish_after_commit(
            DomainEvent(
                name=USER_REACTIVATED,
                organization_id=None,
                user_id=request.user.pk,
                resource_type="user",
                resource_id=str(user.pk),
                metadata={},
            ),
        )
        return Response(AdminUserSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="impersonate")
    def impersonate(self, request, pk: str | None = None):
        """Issue a short-lived access token for the target user.

        The access token carries an ``impersonator_id`` claim and a ``15 minute``
        lifetime. No refresh token is issued for impersonation.
        """
        user = get_object_or_404(User, pk=pk)
        if user.is_superuser and not request.user.is_superuser:
            return Response(
                {"detail": "Only superusers can impersonate other superusers."},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not user.is_active:
            return Response(
                {"detail": "Cannot impersonate an inactive user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        access = AccessToken.for_user(user)
        access.set_exp(lifetime=timedelta(minutes=15))
        access["impersonator_id"] = request.user.pk
        access["impersonator_email"] = request.user.email

        AuditService.log(
            action="user.impersonated",
            resource_type="user",
            resource_id=str(user.pk),
            actor=request.user,
            metadata={"impersonator_id": request.user.pk},
        )
        publish_after_commit(
            DomainEvent(
                name=USER_IMPERSONATED,
                organization_id=None,
                user_id=request.user.pk,
                resource_type="user",
                resource_id=str(user.pk),
                metadata={"impersonator_id": request.user.pk},
            ),
        )
        return Response(
            {
                "access": str(access),
                "user": AdminUserSerializer(user).data,
                "expiresInSeconds": 15 * 60,
            },
            status=status.HTTP_200_OK,
        )


def _revoke_all_sessions(user: User) -> None:
    """Blacklist every outstanding refresh token for the given user."""
    try:
        from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    except ImportError:
        return
    tokens = OutstandingToken.objects.filter(user=user)
    for token_row in tokens:
        try:
            RefreshToken(token_row.token).blacklist()
        except Exception:  # noqa: BLE001
            continue
    # Also mark ``UserSession`` rows revoked if present.
    from talk2record.users.models import UserSession  # noqa: PLC0415

    UserSession.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now(),
    )
