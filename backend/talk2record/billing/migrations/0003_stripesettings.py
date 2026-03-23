from __future__ import annotations

import json

from django.db import migrations, models


def _as_config_dict(raw: object) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, (bytes, bytearray)):
        raw = raw.decode("utf-8")
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return dict(parsed) if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def forwards(apps, schema_editor):
    StripeSettings = apps.get_model("billing", "StripeSettings")
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

        if "integrations_integration" not in tables:
            StripeSettings.objects.get_or_create(
                pk=1,
                defaults={
                    "enabled": True,
                    "config": {"provider": "stripe"},
                    "encrypted_credential": "",
                },
            )
            return

        cursor.execute(
            "SELECT id, enabled, config FROM integrations_integration WHERE slug = %s",
            ["stripe"],
        )
        row = cursor.fetchone()
        encrypted = ""
        if row:
            int_id, enabled, config = row
            if "integrations_apicredential" in tables:
                cursor.execute(
                    "SELECT encrypted_secret FROM integrations_apicredential "
                    "WHERE integration_id = %s",
                    [int_id],
                )
                cred_row = cursor.fetchone()
                if cred_row and cred_row[0]:
                    encrypted = str(cred_row[0])
            StripeSettings.objects.update_or_create(
                pk=1,
                defaults={
                    "enabled": bool(enabled),
                    "config": _as_config_dict(config) or {"provider": "stripe"},
                    "encrypted_credential": encrypted,
                },
            )
        else:
            StripeSettings.objects.get_or_create(
                pk=1,
                defaults={
                    "enabled": True,
                    "config": {"provider": "stripe"},
                    "encrypted_credential": "",
                },
            )


def backwards(apps, schema_editor):
    del apps, schema_editor


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="StripeSettings",
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
                "verbose_name": "Stripe / billing provider settings",
                "verbose_name_plural": "Stripe / billing provider settings",
            },
        ),
        migrations.RunPython(forwards, backwards),
    ]
