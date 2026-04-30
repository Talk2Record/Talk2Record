"""Drop Stripe scaffolding and replace with the Paddle-only billing schema."""

from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


def _delete_stripe_subscriptions(apps, schema_editor):
    """Stripe rows can't be migrated to Paddle automatically — drop them."""

    Subscription = apps.get_model("billing", "Subscription")
    deleted_count, _ = Subscription.objects.filter(provider="stripe").delete()
    if deleted_count:
        print(  # noqa: T201
            f"[billing.0005_paddle_reset] dropped {deleted_count} Stripe-only "
            "Subscription rows (re-seed to recreate against Paddle).",
        )


def _noop(apps, schema_editor):
    return None


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0004_billingproviderconfig_planentitlement_and_more"),
    ]

    operations = [
        migrations.RunPython(_delete_stripe_subscriptions, _noop),
        migrations.DeleteModel(name="StripeSettings"),
        migrations.DeleteModel(name="BillingProviderConfig"),
        migrations.RemoveConstraint(
            model_name="planproviderprice",
            name="unique_plan_provider_interval",
        ),
        migrations.RenameModel(
            old_name="PlanProviderPrice",
            new_name="PlanPrice",
        ),
        migrations.AlterModelOptions(
            name="planprice",
            options={
                "verbose_name": "Plan price",
                "verbose_name_plural": "Plan prices",
                "ordering": ["plan_id", "interval"],
            },
        ),
        migrations.RemoveField(model_name="planprice", name="provider"),
        migrations.RenameField(
            model_name="planprice",
            old_name="provider_price_id",
            new_name="paddle_price_id",
        ),
        migrations.AlterField(
            model_name="planprice",
            name="paddle_price_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="planprice",
            name="amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="planprice",
            name="currency",
            field=models.CharField(default="USD", max_length=8),
        ),
        migrations.AddField(
            model_name="planprice",
            name="billing_cycle",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="planprice",
            name="plan",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="prices",
                to="billing.plan",
            ),
        ),
        migrations.AddConstraint(
            model_name="planprice",
            constraint=models.UniqueConstraint(
                fields=("plan", "interval", "currency"),
                name="unique_plan_interval_currency",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="paddle_product_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name="subscription",
            name="paddle_customer_id",
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="provider",
        ),
        migrations.AlterField(
            model_name="subscription",
            name="status",
            field=models.CharField(
                choices=[
                    ("trialing", "Trialing"),
                    ("active", "Active"),
                    ("paused", "Paused"),
                    ("past_due", "Past due"),
                    ("canceled", "Canceled"),
                ],
                default="trialing",
                max_length=32,
            ),
        ),
        migrations.CreateModel(
            name="PaddleSettings",
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
                (
                    "environment",
                    models.CharField(
                        choices=[
                            ("sandbox", "Sandbox"),
                            ("production", "Production"),
                        ],
                        default="sandbox",
                        max_length=16,
                    ),
                ),
                (
                    "encrypted_api_key",
                    models.TextField(
                        blank=True,
                        help_text="Paddle API key encrypted via SecretVault.",
                    ),
                ),
                (
                    "encrypted_webhook_secret",
                    models.TextField(
                        blank=True,
                        help_text="Webhook signing secret encrypted via SecretVault.",
                    ),
                ),
                ("default_success_url", models.URLField(blank=True)),
                ("default_cancel_url", models.URLField(blank=True)),
                (
                    "paddle_notification_setting_id",
                    models.CharField(blank=True, max_length=64),
                ),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Paddle settings",
                "verbose_name_plural": "Paddle settings",
            },
        ),
    ]
