from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WhatsAppRawPayload",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message_id", models.CharField(max_length=255, unique=True)),
                ("payload", models.JSONField(blank=True, default=dict)),
                ("media_id", models.CharField(blank=True, max_length=255)),
                ("media_url", models.URLField(blank=True)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
                ("processed", models.BooleanField(default=False)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="whatsapp_raw_payloads",
                    to="organizations.organization",
                )),
            ],
            options={
                "ordering": ["-received_at"],
            },
        ),
        migrations.AddIndex(
            model_name="whatsapprawpayload",
            index=models.Index(fields=["organization", "received_at"], name="wa_raw_org_received_idx"),
        ),
        migrations.AddIndex(
            model_name="whatsapprawpayload",
            index=models.Index(fields=["processed", "received_at"], name="wa_raw_processed_idx"),
        ),
    ]
