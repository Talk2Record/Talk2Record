"""Org-scoped DRF endpoints for the WhatsApp app.

Exposes read-only listings of accounts / conversations / messages and an
outbound send endpoint. All endpoints require JWT auth + org membership.
"""

from __future__ import annotations

from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from talk2record.audit.services import AuditService
from talk2record.organizations.permissions import IsOrgAdmin, IsOrgMember
from talk2record.organizations.services import OrganizationContextService
from talk2record.whatsapp.models import (
    WhatsAppAccount,
    WhatsAppConversation,
    WhatsAppMessage,
    WhatsAppTemplate,
)
from talk2record.whatsapp.services.outbound import (
    OutboundSendError,
    WhatsAppOutboundService,
)


class WhatsAppAccountSerializer(serializers.ModelSerializer[WhatsAppAccount]):
    class Meta:
        model = WhatsAppAccount
        fields = [
            "id",
            "phone_number_id",
            "display_number",
            "business_account_id",
            "status",
            "verified_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class WhatsAppConversationSerializer(serializers.ModelSerializer[WhatsAppConversation]):
    account = WhatsAppAccountSerializer(read_only=True)

    class Meta:
        model = WhatsAppConversation
        fields = [
            "id",
            "account",
            "contact_wa_id",
            "contact_name",
            "last_message_at",
            "last_inbound_at",
            "last_outbound_at",
            "created_at",
        ]
        read_only_fields = fields


class WhatsAppMessageSerializer(serializers.ModelSerializer[WhatsAppMessage]):
    class Meta:
        model = WhatsAppMessage
        fields = [
            "id",
            "conversation",
            "wa_message_id",
            "direction",
            "message_type",
            "status",
            "body",
            "media_id",
            "media_url",
            "media_mime",
            "error_code",
            "error_message",
            "timestamp",
            "created_at",
        ]
        read_only_fields = fields


class WhatsAppTemplateSerializer(serializers.ModelSerializer[WhatsAppTemplate]):
    class Meta:
        model = WhatsAppTemplate
        fields = [
            "id",
            "name",
            "language",
            "category",
            "status",
            "components",
            "provider_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class _OrgScopedMixin:
    def _organization(self):
        context = OrganizationContextService.resolve_user_context(self.request.user)
        return context.organization if context else None


class WhatsAppAccountViewSet(_OrgScopedMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = WhatsAppAccountSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return WhatsAppAccount.objects.none()
        return WhatsAppAccount.objects.filter(organization=organization).order_by("-created_at")


class WhatsAppConversationViewSet(_OrgScopedMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = WhatsAppConversationSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return WhatsAppConversation.objects.none()
        return (
            WhatsAppConversation.objects.filter(organization=organization)
            .select_related("account")
            .order_by("-last_message_at", "-created_at")
        )


class WhatsAppMessageViewSet(_OrgScopedMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = WhatsAppMessageSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return WhatsAppMessage.objects.none()
        queryset = WhatsAppMessage.objects.filter(
            organization=organization,
        ).order_by("-created_at")
        conversation_id = self.request.query_params.get("conversation")
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)
        direction = self.request.query_params.get("direction")
        if direction in {
            WhatsAppMessage.Direction.INBOUND,
            WhatsAppMessage.Direction.OUTBOUND,
        }:
            queryset = queryset.filter(direction=direction)
        return queryset


class WhatsAppTemplateViewSet(_OrgScopedMixin, ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = WhatsAppTemplateSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return WhatsAppTemplate.objects.none()
        return WhatsAppTemplate.objects.filter(organization=organization).order_by("name")


class SendWhatsAppMessageSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=32)
    type = serializers.ChoiceField(choices=[("text", "Text"), ("template", "Template")])
    body = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    template_name = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    language_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    components = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
    )

    def validate(self, attrs):
        if attrs["type"] == "text" and not (attrs.get("body") or "").strip():
            msg = "body is required for text messages."
            raise serializers.ValidationError({"body": [msg]})
        if attrs["type"] == "template":
            if not (attrs.get("template_name") or "").strip():
                msg = "template_name is required for template messages."
                raise serializers.ValidationError({"template_name": [msg]})
            if not (attrs.get("language_code") or "").strip():
                msg = "language_code is required for template messages."
                raise serializers.ValidationError({"language_code": [msg]})
        return attrs


class WhatsAppOutboundViewSet(_OrgScopedMixin, GenericViewSet):
    """``POST /api/whatsapp/send/send/`` (action) — admin-only send API."""

    permission_classes = [IsAuthenticated, IsOrgAdmin]

    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        organization = self._organization()
        if organization is None:
            return Response(
                {"detail": "Organization membership required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = SendWhatsAppMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            if data["type"] == "text":
                result = WhatsAppOutboundService.send_text(
                    organization=organization,
                    to=data["to"],
                    body=data["body"],
                    sent_by=request.user,
                )
            else:
                result = WhatsAppOutboundService.send_template(
                    organization=organization,
                    to=data["to"],
                    template_name=data["template_name"],
                    language_code=data["language_code"],
                    components=data.get("components") or [],
                    sent_by=request.user,
                )
        except OutboundSendError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        AuditService.log(
            action="whatsapp.message.sent",
            resource_type="whatsapp_message",
            resource_id=str(result.message.pk),
            actor=request.user,
            organization=organization,
            metadata={
                "to": data["to"],
                "type": data["type"],
                "wa_message_id": result.message.wa_message_id,
            },
        )
        return Response(
            {
                "message": WhatsAppMessageSerializer(result.message).data,
                "provider_response": result.api_response,
            },
            status=status.HTTP_201_CREATED,
        )
