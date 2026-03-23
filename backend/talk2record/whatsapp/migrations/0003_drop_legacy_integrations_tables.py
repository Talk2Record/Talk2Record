from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp", "0002_migrate_from_legacy_integrations"),
        ("ai", "0002_ai_settings"),
        ("billing", "0003_stripesettings"),
    ]

    operations = [
        migrations.RunSQL(
            "DROP TABLE IF EXISTS integrations_apicredential;",
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS integrations_whatsappinboundroute;",
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS integrations_integration;",
            migrations.RunSQL.noop,
        ),
    ]
