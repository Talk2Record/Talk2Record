from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("organizations", "0002_membership"),
        ("users", "0002_user_legal_and_org_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Record",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "source",
                    models.CharField(
                        choices=[("whatsapp", "WhatsApp"), ("upload", "Upload"), ("api", "API")],
                        default="whatsapp",
                        max_length=32,
                    ),
                ),
                ("source_reference", models.CharField(blank=True, max_length=255)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("received", "Received"),
                            ("transcribed", "Transcribed"),
                            ("review", "Review"),
                            ("stored", "Stored"),
                            ("failed", "Failed"),
                        ],
                        default="received",
                        max_length=32,
                    ),
                ),
                ("customer_name", models.CharField(max_length=255)),
                ("product", models.CharField(max_length=255)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("amount", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("currency", models.CharField(default="USD", max_length=8)),
                ("payment_method", models.CharField(blank=True, max_length=64)),
                ("voice_transcript", models.TextField(blank=True)),
                ("confidence_score", models.DecimalField(decimal_places=3, default=0, max_digits=4)),
                ("audio_url", models.URLField(blank=True)),
                ("processing_error", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name="created_records",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="records",
                        to="organizations.organization",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
