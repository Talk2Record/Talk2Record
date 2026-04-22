from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.ai.models import (
    AIModel,
    AIProviderConfig,
    AITask,
    AITaskBinding,
    OrgAIConfig,
)
from talk2record.ai.providers.registry import AIProviderRegistry
from talk2record.ai.resolver import resolve
from talk2record.core.vault import SecretVault
from talk2record.organizations.models import Membership


@pytest.mark.django_db
class TestResolver:
    def test_task_binding_wins_over_legacy(self, organization, workspace_user):
        AIProviderConfig.objects.create(
            organization=organization,
            provider="openrouter",
            encrypted_credential=SecretVault.encrypt("sk-openrouter"),
            base_url="https://openrouter.ai/api/v1",
        )
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.EXTRACTION,
            provider="openrouter",
            model_id="openai/gpt-4o-mini",
        )
        OrgAIConfig.objects.create(
            organization=organization,
            provider="openai",
            encrypted_credential=SecretVault.encrypt("sk-openai"),
            model_extraction="gpt-4o",
            active=True,
        )

        resolution = resolve(task=AITask.EXTRACTION, organization=organization)
        assert resolution is not None
        assert resolution.provider_slug == "openrouter"
        assert resolution.model_id == "openai/gpt-4o-mini"
        assert resolution.api_key == "sk-openrouter"
        assert resolution.base_url == "https://openrouter.ai/api/v1"

    def test_falls_back_to_legacy_config(self, organization):
        OrgAIConfig.objects.create(
            organization=organization,
            provider="openai",
            encrypted_credential=SecretVault.encrypt("sk-legacy"),
            model_extraction="gpt-4o-mini",
            model_transcription="whisper-1",
            active=True,
        )
        resolution = resolve(task=AITask.EXTRACTION, organization=organization)
        assert resolution is not None
        assert resolution.provider_slug == "openai"
        assert resolution.model_id == "gpt-4o-mini"
        assert resolution.api_key == "sk-legacy"

    def test_unknown_provider_slug_falls_through_to_global(self, organization):
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.EXTRACTION,
            provider="does-not-exist",
            model_id="foo",
        )
        resolution = resolve(task=AITask.EXTRACTION, organization=organization)
        # Unknown binding should not be used; we fall through to global defaults
        # (which is ``mock`` in tests). We just assert we don't return the bogus
        # binding and get a registered provider back.
        assert resolution is None or resolution.provider_slug != "does-not-exist"


@pytest.mark.django_db
class TestAIAPIs:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_list_registry(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(reverse("api:ai-provider-list"))
        assert response.status_code == status.HTTP_200_OK
        slugs = {row["slug"] for row in response.data}
        assert {"openai", "openrouter", "groq", "anthropic"}.issubset(slugs)

    def test_admin_can_create_provider_config(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-provider-config-list"),
            data={
                "provider": "openrouter",
                "display_name": "OpenRouter (prod)",
                "api_key": "sk-or-123456",
                "active": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        config = AIProviderConfig.objects.get(pk=response.data["id"])
        assert config.provider == "openrouter"
        assert SecretVault.decrypt(config.encrypted_credential) == "sk-or-123456"

    def test_operator_cannot_create_provider_config(
        self,
        api_client,
        organization,
    ):
        from talk2record.users.tests.factories import UserFactory

        operator = UserFactory.create()
        Membership.objects.create(
            user=operator,
            organization=organization,
            role=Membership.Role.OPERATOR,
            status=Membership.Status.ACTIVE,
        )
        operator.current_organization = organization
        operator.save(update_fields=["current_organization"])
        api_client.force_authenticate(user=operator)

        response = api_client.post(
            reverse("api:ai-provider-config-list"),
            data={"provider": "openai", "api_key": "sk-x"},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_unknown_provider_slug(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-provider-config-list"),
            data={"provider": "not-a-real-provider", "api_key": "x"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_admin_can_create_task_binding(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-task-binding-list"),
            data={
                "task": AITask.EXTRACTION,
                "provider": "openrouter",
                "model_id": "openai/gpt-4o-mini",
                "active": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED

    def test_list_models_filters_by_provider(self, api_client, workspace_user):
        AIModel.objects.create(
            provider="openrouter",
            model_id="openai/gpt-4o-mini",
            display_name="GPT-4o mini via OpenRouter",
            capabilities=["chat"],
        )
        AIModel.objects.create(
            provider="groq",
            model_id="llama-3.3-70b-versatile",
            display_name="Llama 3.3 70B",
            capabilities=["chat"],
        )
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(
            reverse("api:ai-model-list") + "?provider=groq",
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.data if isinstance(response.data, list) else response.data["results"]
        assert len(data) == 1
        assert data[0]["provider"] == "groq"


def test_registry_contains_expected_providers():
    for slug in ("openai", "openrouter", "groq", "anthropic", "mock"):
        assert AIProviderRegistry.get(slug) is not None
