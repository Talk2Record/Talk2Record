from __future__ import annotations

import uuid

from django.db import models


class DomainEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    organization_id = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    resource_type = models.CharField(max_length=64, blank=True)
    resource_id = models.CharField(max_length=128, blank=True)
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["organization_id"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["processed"]),
        ]

    def __str__(self) -> str:
        return f"{self.name}:{self.id}"
