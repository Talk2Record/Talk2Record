"""Platform-staff REST endpoints for billing recovery.

These complement the Django-admin Billing Recovery views by giving the
future React admin area a JSON-driven path to the same
:class:`BillingRecoveryService`. All endpoints are guarded by
:class:`IsPlatformStaff` and return the :class:`BillingResetReport` as
JSON so the UI can render the resulting state without a follow-up GET.
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from talk2record.billing.recovery_service import BillingRecoveryService
from talk2record.organizations.models import Organization
from talk2record.organizations.permissions import IsPlatformStaff

logger = logging.getLogger(__name__)


class BillingResetRequestSerializer(serializers.Serializer):
    """Input contract for the billing-reset endpoint.

    ``reason`` is required so every reset has an audit trail explanation.
    """

    reason = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    also_reset_onboarding = serializers.BooleanField(required=False, default=False)


class AdminOrganizationBillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "slug",
            "status",
            "billing_state_version",
            "profile_setup_completed",
        ]


class AdminOrganizationViewSet(RetrieveModelMixin, GenericViewSet):
    """Read-only org viewset that exposes the billing-reset action.

    Lives under ``/api/admin/organizations/`` (router-prefixed). The list
    endpoint is intentionally omitted — staff users browse orgs via the
    Django admin; this endpoint is only here for the targeted
    ``billing-reset`` action and a minimal RETRIEVE for the future React UI.
    """

    permission_classes = [IsAuthenticated, IsPlatformStaff]
    serializer_class = AdminOrganizationBillingSerializer
    queryset = Organization.objects.all()

    @action(detail=True, methods=["post"], url_path="billing-reset")
    def billing_reset(self, request, pk: str | None = None):
        """Run the 6-step Sync Order against ``pk``.

        Returns the :class:`BillingResetReport` as JSON. Always returns
        ``200 OK`` when the reset ran (even if some Paddle calls reported
        non-fatal errors — those are listed in ``paddle_errors`` so the
        UI can surface them to support).
        """
        organization = get_object_or_404(Organization, pk=pk)
        serializer = BillingResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            report = BillingRecoveryService().reset(
                organization,
                actor=request.user,
                reason=serializer.validated_data["reason"],
                also_reset_onboarding=serializer.validated_data.get(
                    "also_reset_onboarding", False,
                ),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(asdict(report), status=status.HTTP_200_OK)
