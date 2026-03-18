from django.db import migrations
from django.utils import timezone


def seed_legal_documents(apps, schema_editor):
    LegalDocumentVersion = apps.get_model("legal", "LegalDocumentVersion")
    if LegalDocumentVersion.objects.exists():
        return

    effective_at = timezone.now()
    documents = [
        ("privacy-policy", "2026-03-18", "Privacy Policy", "How Talk2Record processes personal data.", True, False),
        ("terms-of-service", "2026-03-18", "Terms of Service", "Contractual terms for using Talk2Record.", True, False),
        (
            "data-processing-agreement",
            "2026-03-18",
            "Data Processing Agreement",
            "Processor terms for customer personal data.",
            False,
            False,
        ),
        (
            "ai-usage-disclaimer",
            "2026-03-18",
            "AI Usage and Disclaimer",
            "Limits and review expectations for AI outputs.",
            False,
            False,
        ),
        ("cookie-policy", "2026-03-18", "Cookie Policy", "Cookie and tracking disclosures.", False, False),
        (
            "acceptable-use-policy",
            "2026-03-18",
            "Acceptable Use Policy",
            "Prohibited activities on Talk2Record.",
            False,
            False,
        ),
        (
            "billing-policy",
            "2026-03-18",
            "Billing Policy",
            "Billing, renewals, refunds, and failed payments.",
            False,
            True,
        ),
    ]

    for document_key, version, title, summary, required_at_signup, required_for_billing in documents:
        LegalDocumentVersion.objects.create(
            document_key=document_key,
            version=version,
            title=title,
            summary=summary,
            required_at_signup=required_at_signup,
            required_for_billing=required_for_billing,
            effective_at=effective_at,
        )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("legal", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_legal_documents, noop_reverse),
    ]
