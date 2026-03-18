from django.conf import settings
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("users", "0002_user_legal_and_org_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocumentVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "document_key",
                    models.CharField(
                        choices=[
                            ("privacy-policy", "Privacy Policy"),
                            ("terms-of-service", "Terms of Service"),
                            ("data-processing-agreement", "Data Processing Agreement"),
                            ("ai-usage-disclaimer", "AI Usage and Disclaimer"),
                            ("cookie-policy", "Cookie Policy"),
                            ("acceptable-use-policy", "Acceptable Use Policy"),
                            ("billing-policy", "Billing Policy"),
                        ],
                        max_length=64,
                    ),
                ),
                ("version", models.CharField(max_length=32)),
                ("title", models.CharField(max_length=255)),
                ("summary", models.TextField(blank=True)),
                ("required_at_signup", models.BooleanField(default=False)),
                ("required_for_billing", models.BooleanField(default=False)),
                ("effective_at", models.DateTimeField()),
                ("published_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={"ordering": ["document_key", "-effective_at"]},
        ),
        migrations.CreateModel(
            name="UserLegalAttestation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "kind",
                    models.CharField(
                        choices=[
                            ("voice-data-consent", "Voice data consent"),
                            ("ai-output-review", "AI output review"),
                            ("record-verification", "Record verification"),
                            ("whatsapp-permission", "WhatsApp permission"),
                            ("billing-autorenewal", "Billing auto-renewal"),
                        ],
                        max_length=64,
                    ),
                ),
                ("context", models.CharField(max_length=64)),
                ("confirmed", models.BooleanField(default=True)),
                ("confirmed_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=512)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="legal_attestations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-confirmed_at"]},
        ),
        migrations.CreateModel(
            name="UserLegalAcceptance",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accepted_at", models.DateTimeField(auto_now_add=True)),
                (
                    "acceptance_source",
                    models.CharField(
                        choices=[
                            ("signup", "Signup"),
                            ("onboarding", "Onboarding"),
                            ("feature_gate", "Feature gate"),
                            ("settings", "Settings"),
                            ("admin", "Admin"),
                        ],
                        max_length=32,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.CharField(blank=True, max_length=512)),
                (
                    "document_version",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="acceptances",
                        to="legal.legaldocumentversion",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.CASCADE,
                        related_name="legal_acceptances",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-accepted_at"]},
        ),
        migrations.AddConstraint(
            model_name="legaldocumentversion",
            constraint=models.UniqueConstraint(
                fields=("document_key", "version"),
                name="unique_legal_document_version",
            ),
        ),
    ]
