"""Refactor AI provider configuration to be application-wide.

Drops the legacy per-organisation tables (``OrgAIConfig``, the old
``AIProviderConfig``, the old org-scoped ``AITaskBinding``) and the JSON
``config`` / ``encrypted_credential`` fields on ``AISettings``. Replaces
them with two global tables:

* ``AIProvider`` -- one row per (category, provider) configuration. At
  most one row per category may have ``is_active=True``.
* ``AITaskBinding`` -- one row per task, mapping it to a model that the
  active provider for that task's category should serve.

Existing rows are intentionally dropped (early-development decision).
"""

from __future__ import annotations

from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0004_aimodel_aiproviderconfig_aitaskbinding"),
    ]

    operations = [
        migrations.DeleteModel(name="OrgAIConfig"),
        migrations.DeleteModel(name="AIProviderConfig"),
        migrations.DeleteModel(name="AITaskBinding"),
        migrations.RemoveField(model_name="aisettings", name="config"),
        migrations.RemoveField(
            model_name="aisettings",
            name="encrypted_credential",
        ),
        migrations.AlterModelOptions(
            name="aisettings",
            options={
                "verbose_name": "AI settings",
                "verbose_name_plural": "AI settings",
            },
        ),
        migrations.CreateModel(
            name="AIProvider",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human label, e.g. 'OpenRouter (prod)'.",
                        max_length=120,
                        unique=True,
                    ),
                ),
                (
                    "slug",
                    models.CharField(
                        help_text=(
                            "Provider slug; must match an entry in the AI "
                            "provider registry."
                        ),
                        max_length=50,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("chat", "Chat / extraction / summarization"),
                            ("transcription", "Transcription"),
                            ("embedding", "Embedding"),
                        ],
                        help_text=(
                            "Capability bucket. The resolver picks the active "
                            "provider per category."
                        ),
                        max_length=20,
                    ),
                ),
                ("display_name", models.CharField(blank=True, max_length=120)),
                (
                    "base_url",
                    models.URLField(
                        blank=True,
                        help_text=(
                            "Override the provider's API base URL (useful for proxies)."
                        ),
                    ),
                ),
                (
                    "encrypted_credential",
                    models.TextField(
                        blank=True,
                        help_text="API key encrypted via SecretVault.",
                    ),
                ),
                (
                    "models_available",
                    models.JSONField(
                        blank=True,
                        default=list,
                        help_text="List of model identifiers this provider exposes.",
                    ),
                ),
                (
                    "default_model",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "Fallback model id when no AITaskBinding row applies."
                        ),
                        max_length=120,
                    ),
                ),
                ("extra_config", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "AI provider",
                "verbose_name_plural": "AI providers",
                "ordering": ["category", "name"],
                "constraints": [
                    models.UniqueConstraint(
                        condition=Q(is_active=True),
                        fields=("category",),
                        name="unique_active_ai_provider_per_category",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="AITaskBinding",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "task",
                    models.CharField(
                        choices=[
                            ("transcription", "Transcription"),
                            ("extraction", "Extraction"),
                            ("summarization", "Summarization"),
                            ("chat", "Chat"),
                            ("embedding", "Embedding"),
                        ],
                        max_length=40,
                        unique=True,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("chat", "Chat / extraction / summarization"),
                            ("transcription", "Transcription"),
                            ("embedding", "Embedding"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "model",
                    models.CharField(
                        help_text=(
                            "Model id forwarded to the active provider for this "
                            "task's category."
                        ),
                        max_length=120,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "AI task binding",
                "verbose_name_plural": "AI task bindings",
                "ordering": ["category", "task"],
            },
        ),
    ]
