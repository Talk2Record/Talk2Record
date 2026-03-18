from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0001_initial"),
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="latest_required_legal_acceptance_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="user",
            name="onboarding_completed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="user",
            name="current_organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name="active_users",
                to="organizations.organization",
            ),
        ),
    ]
