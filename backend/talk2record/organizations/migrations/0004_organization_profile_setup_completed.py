from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organizations", "0003_membershipinvitation"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="profile_setup_completed",
            field=models.BooleanField(default=False),
        ),
    ]
