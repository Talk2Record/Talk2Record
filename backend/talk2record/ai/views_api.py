"""Org-scoped AI configuration APIs.

Endpoints:

* ``GET  /api/ai/providers/``        — list registered provider specs.
* ``GET  /api/ai/models/``           — curated model catalog.
* CRUD ``/api/ai/provider-configs/`` — per-org provider credentials.
* CRUD ``/api/ai/task-bindings/``    — per-org task → (provider, model) bindings.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

from talk2record.ai.models import (
    AIModel,
    AIProviderConfig,
    AITask,
    AITaskBinding,
)
from talk2record.ai.providers.registry import AIProviderRegistry
from talk2record.core.vault import SecretVault
from talk2record.organizations.permissions import IsOrgAdmin, IsOrgMember
from talk2record.organizations.services import OrganizationContextService


class _OrgScopedMixin:
    def _organization(self):
        context = OrganizationContextService.resolve_user_context(self.request.user)
        return context.organization if context else None


class AIProviderRegistrySerializer(serializers.Serializer):
    slug = serializers.CharField()
    display_name = serializers.CharField()
    default_base_url = serializers.CharField()
    capabilities = serializers.ListField(child=serializers.CharField())


class AIProviderRegistryViewSet(GenericViewSet):
    """Read-only listing of registered provider specs."""

    permission_classes = [IsAuthenticated, IsOrgMember]

    def list(self, request):
        data = [
            {
                "slug": spec.slug,
                "display_name": spec.display_name,
                "default_base_url": spec.default_base_url,
                "capabilities": list(spec.capabilities),
            }
            for spec in AIProviderRegistry.all()
        ]
        return Response(data)


class AIModelSerializer(serializers.ModelSerializer[AIModel]):
    class Meta:
        model = AIModel
        fields = [
            "id",
            "provider",
            "model_id",
            "display_name",
            "capabilities",
            "context_window",
            "input_price_per_million",
            "output_price_per_million",
            "active",
        ]
        read_only_fields = fields


class AIModelViewSet(ReadOnlyModelViewSet):
    """Public-to-members view of the curated model catalog."""

    permission_classes = [IsAuthenticated, IsOrgMember]
    serializer_class = AIModelSerializer

    def get_queryset(self):
        queryset = AIModel.objects.filter(active=True).order_by("provider", "model_id")
        provider = self.request.query_params.get("provider")
        if provider:
            queryset = queryset.filter(provider=provider)
        capability = self.request.query_params.get("capability")
        if capability:
            queryset = queryset.filter(capabilities__contains=capability)
        return queryset


class AIProviderConfigSerializer(serializers.ModelSerializer[AIProviderConfig]):
    api_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Plaintext API key; omit to keep the stored credential.",
    )
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = AIProviderConfig
        fields = [
            "id",
            "provider",
            "display_name",
            "base_url",
            "extra_config",
            "active",
            "api_key",
            "api_key_masked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "api_key_masked", "created_at", "updated_at"]

    def get_api_key_masked(self, obj: AIProviderConfig) -> str:
        return SecretVault.mask(obj.encrypted_credential)

    def validate_provider(self, value: str) -> str:
        if AIProviderRegistry.get(value) is None:
            msg = f"Unknown provider slug: {value!r}."
            raise serializers.ValidationError(msg)
        return value


class AIProviderConfigViewSet(_OrgScopedMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdmin]
    serializer_class = AIProviderConfigSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return AIProviderConfig.objects.none()
        return AIProviderConfig.objects.filter(organization=organization).order_by("provider")

    def perform_create(self, serializer):
        organization = self._organization()
        if organization is None:
            msg = "No organisation context available."
            raise serializers.ValidationError(msg)
        api_key = serializer.validated_data.pop("api_key", "").strip()
        encrypted = SecretVault.encrypt(api_key) if api_key else ""
        serializer.save(organization=organization, encrypted_credential=encrypted)

    def perform_update(self, serializer):
        api_key = serializer.validated_data.pop("api_key", "").strip()
        instance = serializer.save()
        if api_key:
            instance.encrypted_credential = SecretVault.encrypt(api_key)
            instance.save(update_fields=["encrypted_credential", "updated_at"])


class AITaskBindingSerializer(serializers.ModelSerializer[AITaskBinding]):
    task = serializers.ChoiceField(choices=AITask.choices)

    class Meta:
        model = AITaskBinding
        fields = [
            "id",
            "task",
            "provider",
            "model_id",
            "active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_provider(self, value: str) -> str:
        if AIProviderRegistry.get(value) is None:
            msg = f"Unknown provider slug: {value!r}."
            raise serializers.ValidationError(msg)
        return value


class AITaskBindingViewSet(_OrgScopedMixin, ModelViewSet):
    permission_classes = [IsAuthenticated, IsOrgAdmin]
    serializer_class = AITaskBindingSerializer

    def get_queryset(self):
        organization = self._organization()
        if organization is None:
            return AITaskBinding.objects.none()
        return AITaskBinding.objects.filter(organization=organization).order_by("task")

    def perform_create(self, serializer):
        organization = self._organization()
        if organization is None:
            msg = "No organisation context available."
            raise serializers.ValidationError(msg)
        serializer.save(organization=organization)

    @action(detail=False, methods=["get"], url_path="tasks")
    def tasks(self, request):
        return Response(
            [{"value": value, "label": label} for value, label in AITask.choices],
        )
