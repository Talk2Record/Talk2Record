from django.db import migrations


def seed_integrations(apps, schema_editor):
    Integration = apps.get_model("integrations", "Integration")
    if Integration.objects.exists():
        return

    Integration.objects.bulk_create(
        [
            Integration(name="WhatsApp", slug="whatsapp", type="whatsapp", config_schema={"requiresEndpoint": True}),
            Integration(name="Stripe", slug="stripe", type="billing", config_schema={"requiresSecret": True}),
            Integration(name="Paddle", slug="paddle", type="billing", config_schema={"requiresSecret": True}),
            Integration(name="Google Sheets", slug="google-sheets", type="automation", config_schema={"requiresSecret": True}),
            Integration(name="Zapier", slug="zapier", type="automation", config_schema={"requiresSecret": True}),
            Integration(name="Webhooks", slug="webhooks", type="webhook", config_schema={"requiresEndpoint": True}),
        ]
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_integrations, noop_reverse),
    ]
