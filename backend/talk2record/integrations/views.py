from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from rest_framework.viewsets import ReadOnlyModelViewSet

from talk2record.audit.services import AuditService
from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import OrganizationIntegration
from talk2record.integrations.serializers import IntegrationConnectionTestSerializer
from talk2record.integrations.serializers import OrganizationIntegrationSerializer
from talk2record.legal.models import UserLegalAttestation
from talk2record.legal.services import LegalAcceptanceService
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership


class OrganizationIntegrationViewSet(ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = OrganizationIntegrationSerializer

    def get_queryset(self):
        return OrganizationIntegration.objects.filter(
            organization__memberships__user=self.request.user,
        ).select_related("organization", "integration")


class IntegrationActionViewSet(GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = IntegrationConnectionTestSerializer

    @action(detail=False, methods=["post"])
    def test_connection(self, request):
        serializer = IntegrationConnectionTestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmedPermission"]:
            return Response(
                {"detail": "Permission to process voice data must be confirmed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        integration = OrganizationIntegration.objects.filter(
            organization__memberships__user=request.user,
            integration__slug=serializer.validated_data["id"],
        ).select_related("organization", "integration").first()
        if integration is None:
            return Response({"detail": "Integration not found."}, status=status.HTTP_404_NOT_FOUND)

        if integration.integration.slug == "whatsapp":
            LegalAcceptanceService.record_attestation(
                user=request.user,
                kind=UserLegalAttestation.Kind.WHATSAPP_PERMISSION,
                context="integration-test",
                metadata={"integration": integration.integration.slug},
                ip_address=request.META.get("REMOTE_ADDR"),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
            )

        secret = serializer.validated_data.get("secret", "")
        if secret:
            ApiCredential.objects.create(
                organization_integration=integration,
                label="Primary credential",
                encrypted_secret=SecretVault.encrypt(secret),
                encrypted_api_key=SecretVault.encrypt(secret),
            )

        endpoint = serializer.validated_data.get("endpoint", "")
        if endpoint:
            integration.endpoint = endpoint
        integration.status = OrganizationIntegration.Status.CONNECTED
        integration.last_sync = timezone.now()
        integration.save(update_fields=["endpoint", "status", "last_sync", "updated_at"])

        integration_name = integration.integration.name
        title = f"{integration_name} integration connected"
        message = f"Your {integration_name} integration has been successfully connected."
        for membership in integration.organization.memberships.filter(
            status=Membership.Status.ACTIVE,
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        ):
            NotificationService.create(
                user=membership.user,
                notification_type=Notification.Type.INTEGRATION_CONNECTED,
                title=title,
                message=message,
                link_url="/dashboard/integrations",
                organization=integration.organization,
                metadata={"integration_id": integration.pk},
            )

        AuditService.log(
            action="integration.tested",
            resource_type="integration",
            resource_id=str(integration.pk),
            actor=request.user,
            organization=integration.organization,
            metadata={"integration": integration.integration.slug},
        )
        return Response(
            {
                "status": f"{integration.integration.name} connection validated.",
                "maskedSecret": SecretVault.mask(secret),
            },
            status=status.HTTP_200_OK,
        )
