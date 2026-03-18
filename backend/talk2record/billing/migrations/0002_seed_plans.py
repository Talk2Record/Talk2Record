from django.db import migrations


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    if Plan.objects.exists():
        return

    Plan.objects.bulk_create(
        [
            Plan(code="starter", name="Starter", base_price=19, currency="USD", region="US", features=["500 notes / month", "Basic dashboard"]),
            Plan(code="growth", name="Growth", base_price=49, currency="USD", region="US", features=["1500 notes / month", "Integrations", "Team workflows"]),
            Plan(code="scale", name="Scale", base_price=99, currency="USD", region="US", features=["5000 notes / month", "Priority support", "Audit logs"]),
        ]
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, noop_reverse),
    ]
