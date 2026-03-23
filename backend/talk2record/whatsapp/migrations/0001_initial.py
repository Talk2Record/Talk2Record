# Generated manually for WhatsAppSettings + WhatsAppInboundRoute.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppSettings",
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
                ("enabled", models.BooleanField(default=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("encrypted_credential", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "WhatsApp Cloud settings",
                "verbose_name_plural": "WhatsApp Cloud settings",
            },
        ),
        migrations.CreateModel(
            name="WhatsAppInboundRoute",
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
                ("phone_number_id", models.CharField(max_length=128, unique=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="whatsapp_inbound_routes",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["phone_number_id"],
            },
        ),
    ]
