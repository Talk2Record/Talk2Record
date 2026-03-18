from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0002_membership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=128)),
                ("category", models.CharField(max_length=64)),
                ("properties", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.CASCADE,
                        related_name="events",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="DailyMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("metric_date", models.DateField()),
                ("voice_processed", models.PositiveIntegerField(default=0)),
                ("records_created", models.PositiveIntegerField(default=0)),
                ("revenue", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("feature_usage", models.PositiveIntegerField(default=0)),
                ("active_users", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="daily_metrics",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["-metric_date"]},
        ),
        migrations.AddConstraint(
            model_name="dailymetric",
            constraint=models.UniqueConstraint(
                fields=("organization", "metric_date"),
                name="unique_daily_metric_per_org_date",
            ),
        ),
    ]
