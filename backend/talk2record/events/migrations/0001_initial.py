import uuid

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DomainEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("name", models.CharField(max_length=128)),
                ("organization_id", models.IntegerField(blank=True, null=True)),
                ("user_id", models.IntegerField(blank=True, null=True)),
                ("resource_type", models.CharField(blank=True, max_length=64)),
                ("resource_id", models.CharField(blank=True, max_length=128)),
                ("payload", models.JSONField(default=dict)),
                ("occurred_at", models.DateTimeField()),
                ("processed", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "indexes": [
                    models.Index(fields=["name"], name="events_doma_name_idx"),
                    models.Index(
                        fields=["organization_id"],
                        name="events_doma_org_id_idx",
                    ),
                    models.Index(
                        fields=["created_at"],
                        name="events_doma_created_idx",
                    ),
                    models.Index(
                        fields=["processed"],
                        name="events_doma_processed_idx",
                    ),
                ],
            },
        ),
    ]
