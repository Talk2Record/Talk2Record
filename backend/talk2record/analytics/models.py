from __future__ import annotations

from django.db import models


class Event(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=128)
    category = models.CharField(max_length=64)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class DailyMetric(models.Model):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="daily_metrics",
    )
    metric_date = models.DateField()
    voice_processed = models.PositiveIntegerField(default=0)
    records_created = models.PositiveIntegerField(default=0)
    revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    feature_usage = models.PositiveIntegerField(default=0)
    active_users = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "metric_date"],
                name="unique_daily_metric_per_org_date",
            ),
        ]
        ordering = ["-metric_date"]

    def __str__(self) -> str:
        return f"{self.organization.name} @ {self.metric_date}"
