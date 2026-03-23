from __future__ import annotations

import json

from django.db import migrations


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
    WhatsAppSettings = apps.get_model("whatsapp", "WhatsAppSettings")
    WhatsAppInboundRoute = apps.get_model("whatsapp", "WhatsAppInboundRoute")
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))

        if "integrations_integration" not in tables:
            WhatsAppSettings.objects.get_or_create(
                pk=1,
                defaults={
                    "enabled": True,
                    "config": {},
                    "encrypted_credential": "",
                },
            )
            return

        cursor.execute(
            "SELECT id, enabled, config FROM integrations_integration WHERE slug = %s",
            ["whatsapp"],
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
            WhatsAppSettings.objects.update_or_create(
                pk=1,
                defaults={
                    "enabled": bool(enabled),
                    "config": _as_config_dict(config),
                    "encrypted_credential": encrypted,
                },
            )
        else:
            WhatsAppSettings.objects.get_or_create(
                pk=1,
                defaults={
                    "enabled": True,
                    "config": {},
                    "encrypted_credential": "",
                },
            )

        if "integrations_whatsappinboundroute" in tables:
            cursor.execute(
                "SELECT phone_number_id, organization_id, created_at, updated_at "
                "FROM integrations_whatsappinboundroute",
            )
            for phone_number_id, org_id, created_at, updated_at in cursor.fetchall():
                WhatsAppInboundRoute.objects.update_or_create(
                    phone_number_id=str(phone_number_id),
                    defaults={
                        "organization_id": org_id,
                        "created_at": created_at,
                        "updated_at": updated_at,
                    },
                )


def backwards(apps, schema_editor):
    del apps, schema_editor


class Migration(migrations.Migration):

    dependencies = [
        ("whatsapp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
