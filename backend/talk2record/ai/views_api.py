"""Global AI configuration APIs (platform-admin only).

Endpoints:

* ``GET  /api/ai/providers/``        -- list registered provider specs.
* ``GET  /api/ai/models/``           -- curated model catalog.
* CRUD ``/api/ai/provider-configs/`` -- global provider credentials.
* CRUD ``/api/ai/task-bindings/``    -- global task -> model bindings.
"""

from __future__ import annotations

from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ReadOnlyModelViewSet

from talk2record.ai.models import (
    AICategory,
    AIModel,
    AIProvider,
    AITask,
    AITaskBinding,
)
from talk2record.ai.providers.registry import AIProviderRegistry
from talk2record.core.vault import SecretVault
from talk2record.organizations.permissions import IsOrgMember, IsPlatformStaff


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


class AIProviderSerializer(serializers.ModelSerializer[AIProvider]):
    api_key = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        help_text="Plaintext API key; omit to keep the stored credential.",
    )
    api_key_masked = serializers.SerializerMethodField()

    class Meta:
        model = AIProvider
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "display_name",
            "base_url",
            "models_available",
            "default_model",
            "extra_config",
            "is_active",
            "api_key",
            "api_key_masked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "api_key_masked", "created_at", "updated_at"]

    def get_api_key_masked(self, obj: AIProvider) -> str:
        return SecretVault.mask(obj.encrypted_credential)

    def validate_slug(self, value: str) -> str:
        if AIProviderRegistry.get(value) is None:
            msg = f"Unknown provider slug: {value!r}."
            raise serializers.ValidationError(msg)
        return value

    def validate_category(self, value: str) -> str:
        valid = {choice.value for choice in AICategory}
        if value not in valid:
            raise serializers.ValidationError(f"Unknown category: {value!r}.")
        return value


class AIProviderViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformStaff]
    serializer_class = AIProviderSerializer
    queryset = AIProvider.objects.all().order_by("category", "name")

    def perform_create(self, serializer):
        api_key = serializer.validated_data.pop("api_key", "").strip()
        encrypted = SecretVault.encrypt(api_key) if api_key else ""
        serializer.save(encrypted_credential=encrypted)

    def perform_update(self, serializer):
        api_key = serializer.validated_data.pop("api_key", "").strip()
        instance = serializer.save()
        if api_key:
            instance.encrypted_credential = SecretVault.encrypt(api_key)
            instance.save(update_fields=["encrypted_credential", "updated_at"])


class AITaskBindingSerializer(serializers.ModelSerializer[AITaskBinding]):
    task = serializers.ChoiceField(choices=AITask.choices)
    category = serializers.ChoiceField(
        choices=AICategory.choices,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = AITaskBinding
        fields = [
            "id",
            "task",
            "category",
            "model",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AITaskBindingViewSet(ModelViewSet):
    permission_classes = [IsAuthenticated, IsPlatformStaff]
    serializer_class = AITaskBindingSerializer
    queryset = AITaskBinding.objects.all().order_by("category", "task")

    @action(detail=False, methods=["get"], url_path="tasks")
    def tasks(self, request):
        return Response(
            [{"value": value, "label": label} for value, label in AITask.choices],
        )
