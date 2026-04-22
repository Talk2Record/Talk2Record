from __future__ import annotations

from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from talk2record.ai.models import OrgAIConfig
from talk2record.core.vault import SecretVault


class OrgAIConfigSerializer(serializers.ModelSerializer):
    api_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Plaintext API key — stored encrypted; omit to keep the current key.",
    )
    api_key_masked = serializers.SerializerMethodField(
        help_text="Last 4 characters of the stored key, masked for display.",
    )

    class Meta:
        model = OrgAIConfig
        fields = [
            "provider",
            "model_transcription",
            "model_extraction",
            "api_key",
            "api_key_masked",
            "active",
        ]
        read_only_fields = ["api_key_masked"]

    def get_api_key_masked(self, obj: OrgAIConfig) -> str:
        return SecretVault.mask(obj.encrypted_credential)


class OrgAIConfigView(APIView):
    """Retrieve or update the AI configuration for the current organisation.

    GET  /api/ai/config/  — returns the current config (masked key).
    PUT  /api/ai/config/  — updates the config; supply api_key to rotate credentials.
    """

    permission_classes = [IsAuthenticated]

    def _get_organization(self, request):
        membership = (
            request.user.memberships.select_related("organization").first()
        )
        org = request.user.current_organization or (
            membership.organization if membership else None
        )
        return org

    def get(self, request):
        org = self._get_organization(request)
        if org is None:
            return Response(
                {"detail": "No organisation found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        config, _ = OrgAIConfig.objects.get_or_create(
            organization=org,
            defaults={
                "provider": OrgAIConfig.Provider.OPENAI,
                "model_transcription": "whisper-1",
                "model_extraction": "gpt-4o",
                "encrypted_credential": "",
                "active": True,
            },
        )
        serializer = OrgAIConfigSerializer(config)
        return Response(serializer.data)

    def put(self, request):
        org = self._get_organization(request)
        if org is None:
            return Response(
                {"detail": "No organisation found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        config, _ = OrgAIConfig.objects.get_or_create(
            organization=org,
            defaults={
                "provider": OrgAIConfig.Provider.OPENAI,
                "model_transcription": "whisper-1",
                "model_extraction": "gpt-4o",
                "encrypted_credential": "",
                "active": True,
            },
        )

        serializer = OrgAIConfigSerializer(config, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        api_key = serializer.validated_data.pop("api_key", "").strip()
        for field, value in serializer.validated_data.items():
            setattr(config, field, value)

        if api_key:
            config.encrypted_credential = SecretVault.encrypt(api_key)

        config.save()
        return Response(OrgAIConfigSerializer(config).data, status=status.HTTP_200_OK)
