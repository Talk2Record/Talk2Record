from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0005_paddle_reset"),
    ]

    operations = [
        migrations.AddField(
            model_name="paddlesettings",
            name="client_side_token",
            field=models.CharField(
                blank=True,
                help_text="Paddle.js client-side token (test_… or live_…). Safe to expose to the browser.",
                max_length=128,
            ),
        ),
        migrations.AddField(
            model_name="paddlesettings",
            name="default_payment_link",
            field=models.URLField(
                blank=True,
                help_text="Approved Paddle payment-link page (must include Paddle.js). Used as checkout.url when creating transactions.",
            ),
        ),
        migrations.AddField(
            model_name="planprice",
            name="trial_period",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Optional trial, e.g. {"interval": "day", "frequency": 14}.',
            ),
        ),
    ]
