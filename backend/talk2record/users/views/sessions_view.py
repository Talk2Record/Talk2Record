"""List and revoke the current user's active sessions (issued refresh tokens)."""

from __future__ import annotations

from contextlib import suppress

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.users.models import UserSession

try:
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from rest_framework_simplejwt.tokens import RefreshToken
except ImportError:
    OutstandingToken = None  # type: ignore[misc, assignment]
    RefreshToken = None  # type: ignore[misc, assignment]


class UserSessionSerializer(serializers.ModelSerializer[UserSession]):
    isCurrent = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            "id",
            "ip_address",
            "user_agent",
            "created_at",
            "last_seen_at",
            "revoked_at",
            "expires_at",
            "isCurrent",
        ]
        read_only_fields = fields

    def get_isCurrent(self, obj: UserSession) -> bool:
        request = self.context.get("request")
        if request is None:
            return False
        return getattr(request, "_user_session_jti", None) == obj.refresh_jti


class UserSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = UserSession.objects.filter(user=request.user).order_by("-created_at")
        serializer = UserSessionSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserSessionRevokeView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, session_id: int):
        session = get_object_or_404(
            UserSession,
            pk=session_id,
            user=request.user,
        )
        if session.revoked_at is not None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])

        if OutstandingToken is None or RefreshToken is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        outstanding = OutstandingToken.objects.filter(
            user=request.user,
            jti=session.refresh_jti,
        ).first()
        if outstanding is not None:
            with suppress(Exception):
                RefreshToken(outstanding.token).blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)
