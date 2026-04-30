from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from talk2record.ai.models import AIModel
from talk2record.ai.models import AIProviderConfig
from talk2record.ai.models import AITask
from talk2record.ai.models import AITaskBinding
from talk2record.billing.models import PaddleSettings
from talk2record.billing.models import Plan
from talk2record.billing.models import PlanEntitlement
from talk2record.billing.models import PlanPrice
from talk2record.core.vault import SecretVault
from talk2record.core.onboarding import OnboardingService
from talk2record.legal.models import LegalDocumentVersion
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.users.tests.factories import UserFactory
from talk2record.whatsapp.models import WhatsAppInboundRoute
from talk2record.whatsapp.models import WhatsAppSettings


def _steps_by_key(report):
    return {step.key: step for step in report.steps}


@pytest.mark.django_db
class TestOnboardingDefaults:
    def test_fresh_database_marks_everything_incomplete(self):
        WhatsAppSettings.objects.all().delete()
        report = OnboardingService.report()
        steps = _steps_by_key(report)

        assert steps["platform.legal_documents"].complete is False
        assert steps["billing.provider_config"].complete is False
        assert steps["ai.provider_config"].complete is False
        assert steps["whatsapp.enabled"].complete is False
        assert steps["organizations.first_org"].complete is False

    def test_report_progress_math(self):
        WhatsAppSettings.objects.all().delete()
        report = OnboardingService.report()
        assert report.total > 0
        assert report.completed == 0
        assert report.percent == 0
        assert report.all_complete is False

    def test_each_step_exposes_admin_url(self):
        WhatsAppSettings.objects.all().delete()
        report = OnboardingService.report()
        for step in report.steps:
            assert step.admin_url, f"step {step.key} has no admin_url"


@pytest.mark.django_db
class TestDependencies:
    def test_ai_task_bindings_blocked_until_provider_exists(self, organization):
        WhatsAppSettings.objects.all().delete()
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.TRANSCRIPTION,
            provider="openai",
            model_id="whisper-1",
            active=True,
        )
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.EXTRACTION,
            provider="openai",
            model_id="gpt-4o",
            active=True,
        )
        report = OnboardingService.report()
        steps = _steps_by_key(report)
        assert steps["ai.task_bindings"].complete is True
        assert steps["ai.provider_config"].complete is False
        assert steps["ai.task_bindings"].blocked_by == "ai.provider_config"

    def test_ai_task_bindings_unblocked_with_provider_config(self, organization):
        WhatsAppSettings.objects.all().delete()
        AIProviderConfig.objects.create(
            organization=organization,
            provider="openai",
            display_name="OpenAI",
            active=True,
        )
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.TRANSCRIPTION,
            provider="openai",
            model_id="whisper-1",
            active=True,
        )
        AITaskBinding.objects.create(
            organization=organization,
            task=AITask.EXTRACTION,
            provider="openai",
            model_id="gpt-4o",
            active=True,
        )
        report = OnboardingService.report()
        steps = _steps_by_key(report)
        assert steps["ai.provider_config"].complete is True
        assert steps["ai.task_bindings"].complete is True
        assert steps["ai.task_bindings"].blocked_by is None

    def test_whatsapp_route_blocked_until_settings_enabled(self, organization):
        WhatsAppInboundRoute.objects.create(
            organization=organization,
            phone_number_id="999000111",
        )
        settings = WhatsAppSettings.get_solo()
        settings.enabled = False
        settings.encrypted_credential = ""
        settings.save()

        report = OnboardingService.report()
        steps = _steps_by_key(report)
        assert steps["whatsapp.enabled"].complete is False
        assert steps["whatsapp.inbound_route"].blocked_by == "whatsapp.enabled"

    def test_plan_with_price_requires_price_row(self):
        WhatsAppSettings.objects.all().delete()
        Plan.objects.create(code="starter", name="Starter", base_price=Decimal("9.00"))
        report = OnboardingService.report()
        steps = _steps_by_key(report)
        assert steps["billing.plan_with_price"].complete is False

        plan = Plan.objects.get(code="starter")
        PlanPrice.objects.create(
            plan=plan,
            paddle_price_id="pri_test",
            interval="month",
            amount=Decimal("9.00"),
            currency="USD",
        )
        report = OnboardingService.report()
        steps = _steps_by_key(report)
        assert steps["billing.plan_with_price"].complete is True


@pytest.mark.django_db
class TestStepCompletion:
    def test_billing_provider_config_flips_on_create(self):
        WhatsAppSettings.objects.all().delete()
        before = _steps_by_key(OnboardingService.report())
        assert before["billing.provider_config"].complete is False

        settings = PaddleSettings.get_solo()
        settings.enabled = True
        settings.encrypted_api_key = SecretVault.encrypt("pdl_test_secret")
        settings.save(
            update_fields=["enabled", "encrypted_api_key", "updated_at"],
        )
        after = _steps_by_key(OnboardingService.report())
        assert after["billing.provider_config"].complete is True

    def test_plan_entitlement_marks_optional_step(self):
        WhatsAppSettings.objects.all().delete()
        plan = Plan.objects.create(
            code="pro", name="Pro", base_price=Decimal("29.00"),
        )
        PlanEntitlement.objects.create(plan=plan, feature_key="ai.usage", enabled=True)
        steps = _steps_by_key(OnboardingService.report())
        assert steps["billing.entitlements"].complete is True
        assert steps["billing.entitlements"].optional is True

    def test_legal_requires_both_terms_and_privacy(self):
        WhatsAppSettings.objects.all().delete()
        LegalDocumentVersion.objects.create(
            document_key=LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE,
            version="1.0",
            title="Terms",
            effective_at=timezone.now(),
            is_active=True,
        )
        steps = _steps_by_key(OnboardingService.report())
        assert steps["platform.legal_documents"].complete is False

        LegalDocumentVersion.objects.create(
            document_key=LegalDocumentVersion.DocumentKey.PRIVACY_POLICY,
            version="1.0",
            title="Privacy",
            effective_at=timezone.now(),
            is_active=True,
        )
        steps = _steps_by_key(OnboardingService.report())
        assert steps["platform.legal_documents"].complete is True

    def test_ai_models_seeded(self):
        WhatsAppSettings.objects.all().delete()
        steps = _steps_by_key(OnboardingService.report())
        assert steps["ai.models_seeded"].complete is False

        AIModel.objects.create(
            provider="openai",
            model_id="whisper-1",
            display_name="Whisper",
            capabilities=["transcription"],
        )
        steps = _steps_by_key(OnboardingService.report())
        assert steps["ai.models_seeded"].complete is True

    def test_first_organization_requires_active_owner(self):
        WhatsAppSettings.objects.all().delete()
        steps = _steps_by_key(OnboardingService.report())
        assert steps["organizations.first_org"].complete is False

        org = Organization.objects.create(name="Example", slug="example")
        steps = _steps_by_key(OnboardingService.report())
        assert steps["organizations.first_org"].complete is False

        owner = UserFactory.create()
        Membership.objects.create(
            user=owner,
            organization=org,
            role=Membership.Role.OWNER,
            status=Membership.Status.ACTIVE,
        )
        steps = _steps_by_key(OnboardingService.report())
        assert steps["organizations.first_org"].complete is True


@pytest.mark.django_db
class TestProgressMath:
    def test_progress_counts_only_required_steps(self):
        WhatsAppSettings.objects.all().delete()
        report_empty = OnboardingService.report()
        required_total = report_empty.total
        optional_total = report_empty.optional_total
        assert required_total >= 1
        assert optional_total >= 1
        assert report_empty.completed == 0

    def test_progress_percentage_updates_when_step_completes(self):
        WhatsAppSettings.objects.all().delete()
        empty_report = OnboardingService.report()
        assert empty_report.percent == 0

        AIModel.objects.create(
            provider="openai",
            model_id="gpt-4o",
            display_name="GPT-4o",
            capabilities=["chat"],
        )
        after = OnboardingService.report()
        assert after.percent > empty_report.percent
        assert after.completed == empty_report.completed + 1
