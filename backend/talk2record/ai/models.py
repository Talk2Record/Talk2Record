from __future__ import annotations

from django.db import models


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
