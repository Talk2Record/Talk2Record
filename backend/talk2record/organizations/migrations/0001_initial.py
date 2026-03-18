from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("slug", models.SlugField(unique=True)),
                ("region", models.CharField(blank=True, max_length=64)),
                ("timezone", models.CharField(default="UTC", max_length=64)),
                ("default_currency", models.CharField(default="USD", max_length=8)),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("past_due", "Past due"), ("suspended", "Suspended")],
                        default="active",
                        max_length=32,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["name"]},
        ),
    ]
