from __future__ import annotations

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Record",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(
                    choices=[("whatsapp", "WhatsApp"), ("upload", "Upload"), ("api", "API")],
                    default="whatsapp",
                    max_length=32,
                )),
                ("source_reference", models.CharField(blank=True, max_length=255)),
                ("type", models.CharField(
                    choices=[("voice_note", "Voice Note"), ("call", "Call"), ("meeting", "Meeting"), ("document", "Document")],
                    default="voice_note",
                    max_length=32,
                )),
                ("status", models.CharField(
                    choices=[
                        ("received", "Received"), ("transcribing", "Transcribing"),
                        ("transcribed", "Transcribed"), ("extracting", "Extracting"),
                        ("extracted", "Extracted"), ("review", "Review"),
                        ("stored", "Stored"), ("failed", "Failed"), ("dead_letter", "Dead letter"),
                    ],
                    default="received",
                    max_length=32,
                )),
                ("audio_url", models.URLField(blank=True)),
                ("media_id", models.CharField(blank=True, max_length=255)),
                ("processing_error", models.TextField(blank=True)),
                ("processing_error_step", models.CharField(blank=True, max_length=32)),
                ("processing_retry_count", models.PositiveSmallIntegerField(default=0)),
                ("last_failed_at", models.DateTimeField(blank=True, null=True)),
                ("dead_lettered_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="records",
                    to="organizations.organization",
                )),
                ("created_by", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="created_records",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RecordSchema",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("version", models.CharField(max_length=20)),
                ("definition", models.JSONField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RecordArtifact",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=100)),
                ("artifact_type", models.CharField(
                    choices=[("text", "Text"), ("json", "JSON"), ("number", "Number"), ("file", "File")],
                    default="text",
                    max_length=50,
                )),
                ("content", models.JSONField()),
                ("provider", models.CharField(blank=True, max_length=64)),
                ("model", models.CharField(blank=True, max_length=64)),
                ("prompt_version", models.CharField(blank=True, max_length=32)),
                ("schema_version", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("record", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="artifacts",
                    to="records.record",
                )),
            ],
            options={
                "ordering": ["key", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="RecordProcessingState",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(
                    choices=[
                        ("received", "Received"), ("transcribing", "Transcribing"),
                        ("transcribed", "Transcribed"), ("extracting", "Extracting"),
                        ("extracted", "Extracted"), ("review", "Review"),
                        ("stored", "Stored"), ("failed", "Failed"), ("dead_letter", "Dead letter"),
                    ],
                    max_length=32,
                )),
                ("details", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now_add=True)),
                ("record", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="processing_states",
                    to="records.record",
                )),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="record",
            constraint=models.UniqueConstraint(
                condition=~models.Q(source_reference=""),
                fields=["source", "source_reference"],
                name="unique_record_source_reference_per_source",
            ),
        ),
        migrations.AddIndex(
            model_name="record",
            index=models.Index(fields=["organization", "created_at"], name="record_org_created_idx"),
        ),
        migrations.AddIndex(
            model_name="record",
            index=models.Index(fields=["status", "updated_at"], name="record_status_updated_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="recordartifact",
            unique_together={("record", "key")},
        ),
        migrations.AddIndex(
            model_name="recordartifact",
            index=models.Index(fields=["record", "key"], name="artifact_record_key_idx"),
        ),
        migrations.AddIndex(
            model_name="recordartifact",
            index=models.Index(fields=["key", "created_at"], name="artifact_key_created_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="recordschema",
            unique_together={("name", "version")},
        ),
        migrations.AddIndex(
            model_name="recordprocessingstate",
            index=models.Index(fields=["record", "updated_at"], name="record_state_timeline_idx"),
        ),
        migrations.AddIndex(
            model_name="recordprocessingstate",
            index=models.Index(fields=["status", "updated_at"], name="record_state_status_idx"),
        ),
    ]
