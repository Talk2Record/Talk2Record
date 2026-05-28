from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.ai.models import AICategory
from talk2record.ai.models import AIModel
from talk2record.ai.models import AIProvider
from talk2record.ai.models import AITask
from talk2record.ai.models import AITaskBinding
from talk2record.ai.providers.registry import AIProviderRegistry
from talk2record.ai.resolver import resolve
from talk2record.core.vault import SecretVault
from talk2record.organizations.models import Membership


@pytest.mark.django_db
class TestResolver:
    def test_resolves_active_chat_provider(self):
        AIProvider.objects.create(
            name="OpenRouter prod",
            slug="openrouter",
            category=AICategory.CHAT,
            base_url="https://openrouter.ai/api/v1",
            encrypted_credential=SecretVault.encrypt("sk-openrouter"),
            models_available=["openai/gpt-4o-mini", "openrouter/auto"],
            default_model="openrouter/auto",
            is_active=True,
        )
        AITaskBinding.objects.create(
            task=AITask.EXTRACTION,
            category=AICategory.CHAT,
            model="openai/gpt-4o-mini",
        )

        resolution = resolve(task=AITask.EXTRACTION)

        assert resolution is not None
        assert resolution.provider_slug == "openrouter"
        assert resolution.model_id == "openai/gpt-4o-mini"
        assert resolution.api_key == "sk-openrouter"
        assert resolution.base_url == "https://openrouter.ai/api/v1"

    def test_falls_back_to_default_model_when_no_binding(self):
        AIProvider.objects.create(
            name="OpenRouter prod",
            slug="openrouter",
            category=AICategory.CHAT,
            encrypted_credential=SecretVault.encrypt("sk-x"),
            models_available=["openrouter/auto"],
            default_model="openrouter/auto",
            is_active=True,
        )
        resolution = resolve(task=AITask.SUMMARIZATION)
        assert resolution is not None
        assert resolution.model_id == "openrouter/auto"

    def test_returns_none_when_no_active_provider(self):
        assert resolve(task=AITask.EXTRACTION) is None

    def test_saving_active_provider_deactivates_same_category(self):
        first = AIProvider.objects.create(
            name="OpenRouter",
            slug="openrouter",
            category=AICategory.CHAT,
            models_available=["openrouter/auto"],
            default_model="openrouter/auto",
            is_active=True,
        )
        AIProvider.objects.create(
            name="Groq",
            slug="groq",
            category=AICategory.CHAT,
            models_available=["llama-3.3-70b-versatile"],
            default_model="llama-3.3-70b-versatile",
            is_active=True,
        )
        first.refresh_from_db()
        assert first.is_active is False

    def test_active_provider_in_other_category_unaffected(self):
        AIProvider.objects.create(
            name="OpenAI Whisper",
            slug="openai",
            category=AICategory.TRANSCRIPTION,
            models_available=["whisper-1"],
            default_model="whisper-1",
            is_active=True,
        )
        AIProvider.objects.create(
            name="OpenRouter",
            slug="openrouter",
            category=AICategory.CHAT,
            models_available=["openrouter/auto"],
            default_model="openrouter/auto",
            is_active=True,
        )
        assert AIProvider.objects.filter(is_active=True).count() == 2

    def test_provider_slug_must_support_category(self):
        with pytest.raises(ValidationError):
            AIProvider.objects.create(
                name="OpenRouter (transcription)",
                slug="openrouter",
                category=AICategory.TRANSCRIPTION,
                models_available=["whisper-1"],
                default_model="whisper-1",
                is_active=True,
            )

    def test_task_binding_model_validated_against_active_provider(self):
        AIProvider.objects.create(
            name="OpenRouter",
            slug="openrouter",
            category=AICategory.CHAT,
            models_available=["openrouter/auto"],
            default_model="openrouter/auto",
            is_active=True,
        )
        with pytest.raises(ValidationError):
            AITaskBinding.objects.create(
                task=AITask.EXTRACTION,
                category=AICategory.CHAT,
                model="not-in-list",
            )


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

    def test_staff_can_create_provider(self, api_client, workspace_user):
        workspace_user.is_staff = True
        workspace_user.save(update_fields=["is_staff"])
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-provider-config-list"),
            data={
                "name": "OpenRouter prod",
                "slug": "openrouter",
                "category": AICategory.CHAT.value,
                "models_available": ["openai/gpt-4o-mini"],
                "default_model": "openai/gpt-4o-mini",
                "api_key": "sk-or-123456",
                "is_active": True,
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data
        provider = AIProvider.objects.get(pk=response.data["id"])
        assert provider.slug == "openrouter"
        assert SecretVault.decrypt(provider.encrypted_credential) == "sk-or-123456"

    def test_non_staff_member_cannot_create_provider(self, api_client, organization):
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
            data={
                "name": "x",
                "slug": "openai",
                "category": AICategory.CHAT.value,
                "api_key": "sk-x",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_unknown_provider_slug(self, api_client, workspace_user):
        workspace_user.is_staff = True
        workspace_user.save(update_fields=["is_staff"])
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-provider-config-list"),
            data={
                "name": "x",
                "slug": "not-a-real-provider",
                "category": AICategory.CHAT.value,
                "api_key": "x",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_staff_can_create_task_binding(self, api_client, workspace_user):
        workspace_user.is_staff = True
        workspace_user.save(update_fields=["is_staff"])
        AIProvider.objects.create(
            name="OpenRouter",
            slug="openrouter",
            category=AICategory.CHAT,
            models_available=["openai/gpt-4o-mini"],
            default_model="openai/gpt-4o-mini",
            is_active=True,
        )
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse("api:ai-task-binding-list"),
            data={
                "task": AITask.EXTRACTION,
                "category": AICategory.CHAT.value,
                "model": "openai/gpt-4o-mini",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED, response.data

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
        data = (
            response.data
            if isinstance(response.data, list)
            else response.data["results"]
        )
        assert len(data) == 1
        assert data[0]["provider"] == "groq"


def test_registry_contains_expected_providers():
    for slug in ("openai", "openrouter", "groq", "anthropic", "mock"):
        assert AIProviderRegistry.get(slug) is not None
