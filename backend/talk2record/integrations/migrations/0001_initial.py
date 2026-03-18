from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0002_membership"),
    ]

    operations = [
        migrations.CreateModel(
            name="Integration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=64)),
                ("slug", models.SlugField(unique=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("whatsapp", "WhatsApp"),
                            ("billing", "Billing"),
                            ("automation", "Automation"),
                            ("webhook", "Webhook"),
                            ("analytics", "Analytics"),
                        ],
                        max_length=32,
                    ),
                ),
                ("enabled", models.BooleanField(default=True)),
                ("config_schema", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="OrganizationIntegration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("connected", "Connected"),
                            ("attention", "Attention"),
                            ("available", "Available"),
                        ],
                        default="available",
                        max_length=32,
                    ),
                ),
                ("endpoint", models.URLField(blank=True)),
                ("encrypted_config", models.JSONField(blank=True, default=dict)),
                ("last_sync", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "integration",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="organization_integrations",
                        to="integrations.integration",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="integrations",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["organization__name", "integration__name"]},
        ),
        migrations.CreateModel(
            name="ApiCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label", models.CharField(max_length=128)),
                ("encrypted_api_key", models.TextField(blank=True)),
                ("encrypted_secret", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization_integration",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="credentials",
                        to="integrations.organizationintegration",
                    ),
                ),
            ],
            options={"ordering": ["organization_integration__organization__name", "label"]},
        ),
        migrations.AddConstraint(
            model_name="organizationintegration",
            constraint=models.UniqueConstraint(
                fields=("organization", "integration"),
                name="unique_organization_integration",
            ),
        ),
    ]
