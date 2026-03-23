from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class AISettings(models.Model):
    """Singleton (``pk=1``) for AI provider config and encrypted API credential."""

    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    encrypted_credential = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("AI provider settings")
        verbose_name_plural = _("AI provider settings")

    def __str__(self) -> str:
        return "AI"

    @classmethod
    def get_solo(cls) -> AISettings:
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                "enabled": True,
                "config": {},
                "encrypted_credential": "",
            },
        )
        return obj


class AIPromptTemplate(models.Model):
    name = models.CharField(max_length=100)
    provider = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    prompt_text = models.TextField()
    version = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "provider", "model", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "provider", "model", "version"],
                name="unique_prompt_template_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.provider}:{self.model}:v{self.version}"
