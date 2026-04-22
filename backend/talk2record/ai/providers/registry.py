"""Registry of AI providers and their metadata.

This module is the single source of truth for which provider slugs the
platform knows about, how to build provider instances, and what
capabilities each provider supports. Adding a new provider is a matter of
creating a small adapter and registering it here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class ProviderSpec:
    """Static metadata describing a registered AI provider."""

    slug: str
    display_name: str
    default_base_url: str = ""
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    chat_factory: Callable[..., Any] | None = None
    transcription_factory: Callable[..., Any] | None = None

    def supports(self, capability: str) -> bool:
        return capability in self.capabilities


class AIProviderRegistry:
    """Global registry mapping provider slugs to ``ProviderSpec`` entries."""

    _providers: dict[str, ProviderSpec] = {}

    @classmethod
    def register(cls, spec: ProviderSpec) -> None:
        cls._providers[spec.slug] = spec

    @classmethod
    def get(cls, slug: str) -> ProviderSpec | None:
        return cls._providers.get(slug)

    @classmethod
    def require(cls, slug: str) -> ProviderSpec:
        spec = cls.get(slug)
        if spec is None:
            msg = f"Unknown AI provider slug: {slug!r}"
            raise KeyError(msg)
        return spec

    @classmethod
    def slugs(cls) -> list[str]:
        return sorted(cls._providers.keys())

    @classmethod
    def all(cls) -> list[ProviderSpec]:
        return [cls._providers[s] for s in cls.slugs()]

    @classmethod
    def clear(cls) -> None:  # pragma: no cover - only used in tests
        cls._providers.clear()


def _build_default_registry() -> None:
    """Seed the registry with the built-in providers.

    Factories are imported lazily to avoid a hard import dependency when
    optional SDKs (openai, anthropic) are not installed in every environment.
    """

    from talk2record.ai.providers.anthropic import AnthropicExtractionProvider
    from talk2record.ai.providers.mock import (
        MockExtractionProvider,
        MockTranscriptionProvider,
    )
    from talk2record.ai.providers.openai import (
        OpenAIExtractionProvider,
        OpenAITranscriptionProvider,
    )
    from talk2record.ai.providers.openai_compat import (
        OpenAICompatibleExtractionProvider,
    )

    AIProviderRegistry.register(
        ProviderSpec(
            slug="mock",
            display_name="Mock (testing)",
            capabilities=("chat", "transcription"),
            chat_factory=lambda *, api_key="", model="", base_url="": MockExtractionProvider(),
            transcription_factory=(
                lambda *, api_key="", model="", base_url="": MockTranscriptionProvider()
            ),
        ),
    )

    AIProviderRegistry.register(
        ProviderSpec(
            slug="openai",
            display_name="OpenAI",
            default_base_url="https://api.openai.com/v1",
            capabilities=("chat", "transcription", "embedding", "vision"),
            chat_factory=lambda *, api_key="", model="", base_url="": (
                OpenAIExtractionProvider(api_key=api_key, model=model or "gpt-4o")
            ),
            transcription_factory=lambda *, api_key="", model="", base_url="": (
                OpenAITranscriptionProvider(
                    api_key=api_key,
                    model=model or "whisper-1",
                )
            ),
        ),
    )

    AIProviderRegistry.register(
        ProviderSpec(
            slug="openrouter",
            display_name="OpenRouter",
            default_base_url="https://openrouter.ai/api/v1",
            capabilities=("chat",),
            chat_factory=lambda *, api_key="", model="", base_url="": (
                OpenAICompatibleExtractionProvider(
                    provider_name="openrouter",
                    api_key=api_key,
                    model=model or "openrouter/auto",
                    base_url=base_url or "https://openrouter.ai/api/v1",
                )
            ),
        ),
    )

    AIProviderRegistry.register(
        ProviderSpec(
            slug="groq",
            display_name="Groq",
            default_base_url="https://api.groq.com/openai/v1",
            capabilities=("chat", "transcription"),
            chat_factory=lambda *, api_key="", model="", base_url="": (
                OpenAICompatibleExtractionProvider(
                    provider_name="groq",
                    api_key=api_key,
                    model=model or "llama-3.3-70b-versatile",
                    base_url=base_url or "https://api.groq.com/openai/v1",
                )
            ),
            transcription_factory=lambda *, api_key="", model="", base_url="": (
                OpenAITranscriptionProvider(
                    api_key=api_key,
                    model=model or "whisper-large-v3",
                    base_url=base_url or "https://api.groq.com/openai/v1",
                )
            ),
        ),
    )

    AIProviderRegistry.register(
        ProviderSpec(
            slug="anthropic",
            display_name="Anthropic",
            default_base_url="https://api.anthropic.com",
            capabilities=("chat", "vision"),
            chat_factory=lambda *, api_key="", model="", base_url="": (
                AnthropicExtractionProvider(
                    api_key=api_key,
                    model=model or "claude-3-5-sonnet-20241022",
                )
            ),
        ),
    )


_build_default_registry()
