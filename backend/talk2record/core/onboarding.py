"""Central onboarding checklist for the Django admin overview page.

Each :class:`OnboardingStep` describes one installation milestone (legal docs,
billing provider credentials, WhatsApp settings, first organisation, ...). The
``OnboardingService`` evaluates every step against the current database and
returns a list that the admin dashboard renders as a progress checklist.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from dataclasses import field

from django.db.models import Count
from django.urls import NoReverseMatch
from django.urls import reverse


@dataclass(frozen=True)
class OnboardingStep:
    key: str
    title: str
    description: str
    group: str
    admin_url: str
    complete: bool
    blocked_by: str | None = None
    optional: bool = False

    @property
    def required(self) -> bool:
        return not self.optional


@dataclass(frozen=True)
class _StepSpec:
    key: str
    title: str
    description: str
    group: str
    check: Callable[[], bool]
    admin_url_name: str
    admin_url_empty_name: str | None = None
    depends_on: str | None = None
    optional: bool = False

    def resolve_url(self, complete: bool) -> str:
        name = self.admin_url_name
        if not complete and self.admin_url_empty_name:
            name = self.admin_url_empty_name
        try:
            return reverse(name)
        except NoReverseMatch:
            return ""


def _check_legal_documents() -> bool:
    from talk2record.legal.models import LegalDocumentVersion

    required_keys = {
        LegalDocumentVersion.DocumentKey.TERMS_OF_SERVICE,
        LegalDocumentVersion.DocumentKey.PRIVACY_POLICY,
    }
    present = set(
        LegalDocumentVersion.objects.filter(
            is_active=True,
            document_key__in=list(required_keys),
        ).values_list("document_key", flat=True),
    )
    return required_keys.issubset(present)


def _check_site_configured() -> bool:
    try:
        from django.contrib.sites.models import Site
    except Exception:
        return True
    site = Site.objects.first()
    if site is None:
        return False
    domain = (site.domain or "").lower()
    return bool(domain) and domain != "example.com"


def _check_paddle_configured() -> bool:
    from talk2record.billing.models import PaddleSettings

    try:
        settings = PaddleSettings.get_solo()
    except Exception:
        return False
    return bool(settings.enabled and settings.encrypted_api_key)


def _check_plan_with_price() -> bool:
    from talk2record.billing.models import Plan

    return (
        Plan.objects.annotate(
            price_count=Count("prices"),
        )
        .filter(price_count__gt=0)
        .exists()
    )


def _check_plan_entitlements() -> bool:
    from talk2record.billing.models import PlanEntitlement

    return PlanEntitlement.objects.exists()


def _check_ai_provider_config() -> bool:
    from talk2record.ai.models import AIProvider

    return AIProvider.objects.filter(is_active=True).exists()


def _check_ai_models_seeded() -> bool:
    from talk2record.ai.models import AIModel

    return AIModel.objects.exists()


def _check_ai_task_bindings() -> bool:
    from talk2record.ai.models import AITask
    from talk2record.ai.models import AITaskBinding

    required = {AITask.TRANSCRIPTION, AITask.EXTRACTION}
    present = set(
        AITaskBinding.objects.filter(task__in=list(required)).values_list(
            "task",
            flat=True,
        ),
    )
    return required.issubset(present)


def _check_whatsapp_enabled() -> bool:
    from talk2record.whatsapp.models import WhatsAppSettings

    try:
        settings = WhatsAppSettings.get_solo()
    except Exception:
        return False
    return bool(settings.enabled and settings.encrypted_credential)


def _check_whatsapp_inbound_route() -> bool:
    from talk2record.whatsapp.models import WhatsAppInboundRoute

    return WhatsAppInboundRoute.objects.exists()


def _check_first_organization() -> bool:
    from talk2record.organizations.models import Organization

    # Any organisation row counts — staff often create the tenant via admin or
    # the first member may be admin/operator rather than owner; requiring an
    # active *owner* membership incorrectly left this step incomplete.
    return Organization.objects.exists()


_STEPS: tuple[_StepSpec, ...] = (
    _StepSpec(
        key="platform.legal_documents",
        title="Publish legal documents",
        description=(
            "Create active Terms of Service and Privacy Policy versions. "
            "Users must accept these before signup completes."
        ),
        group="Platform",
        check=_check_legal_documents,
        admin_url_name="admin:legal_legaldocumentversion_changelist",
        admin_url_empty_name="admin:legal_legaldocumentversion_add",
    ),
    _StepSpec(
        key="platform.site_configured",
        title="Configure site domain",
        description=(
            "Point the Django Site object at your real domain (currently "
            "example.com). Outbound emails and links use this value."
        ),
        group="Platform",
        check=_check_site_configured,
        admin_url_name="admin:sites_site_changelist",
        optional=True,
    ),
    _StepSpec(
        key="billing.provider_config",
        title="Connect Paddle",
        description=(
            "Add a Paddle API key (sandbox or production) and webhook secret "
            "so organisations can subscribe."
        ),
        group="Billing",
        check=_check_paddle_configured,
        admin_url_name="admin:billing_paddlesettings_changelist",
        admin_url_empty_name="admin:billing_paddlesettings_changelist",
    ),
    _StepSpec(
        key="billing.plan_with_price",
        title="Publish a plan with a price",
        description=(
            "Create at least one Plan and a PlanPrice tied to it. Plans without "
            "a synced Paddle price cannot be used at checkout."
        ),
        group="Billing",
        check=_check_plan_with_price,
        admin_url_name="admin:billing_plan_changelist",
        admin_url_empty_name="admin:billing_plan_add",
        depends_on="billing.provider_config",
    ),
    _StepSpec(
        key="billing.entitlements",
        title="Add plan entitlements",
        description=(
            "Describe what each plan includes (feature flags and usage limits) "
            "so the Entitlements API can gate features."
        ),
        group="Billing",
        check=_check_plan_entitlements,
        admin_url_name="admin:billing_planentitlement_changelist",
        admin_url_empty_name="admin:billing_planentitlement_add",
        depends_on="billing.plan_with_price",
        optional=True,
    ),
    _StepSpec(
        key="ai.provider_config",
        title="Connect an AI provider",
        description=(
            "Add credentials for OpenAI, OpenRouter, Groq, Anthropic, or another "
            "registered provider. Required before transcription and extraction."
        ),
        group="AI",
        check=_check_ai_provider_config,
        admin_url_name="admin:ai_aiprovider_changelist",
        admin_url_empty_name="admin:ai_aiprovider_add",
    ),
    _StepSpec(
        key="ai.models_seeded",
        title="Seed the AI model catalog",
        description=(
            "Curate the AI models staff can select from. Include at least one "
            "transcription model and one chat model."
        ),
        group="AI",
        check=_check_ai_models_seeded,
        admin_url_name="admin:ai_aimodel_changelist",
        admin_url_empty_name="admin:ai_aimodel_add",
    ),
    _StepSpec(
        key="ai.task_bindings",
        title="Bind transcription and extraction tasks",
        description=(
            "Map AI tasks (transcription, extraction) to a provider/model pair "
            "so the resolver knows which model to route each job to."
        ),
        group="AI",
        check=_check_ai_task_bindings,
        admin_url_name="admin:ai_aitaskbinding_changelist",
        admin_url_empty_name="admin:ai_aitaskbinding_add",
        depends_on="ai.provider_config",
    ),
    _StepSpec(
        key="whatsapp.enabled",
        title="Enable WhatsApp Cloud",
        description=(
            "Turn on WhatsApp integration and store the access token. The "
            "inbound webhook refuses messages until this is set."
        ),
        group="WhatsApp",
        check=_check_whatsapp_enabled,
        admin_url_name="admin:whatsapp_whatsappsettings_changelist",
    ),
    _StepSpec(
        key="whatsapp.inbound_route",
        title="Register an inbound phone route",
        description=(
            "Associate a WhatsApp phone_number_id with an organisation so "
            "inbound messages can be routed to the right workspace."
        ),
        group="WhatsApp",
        check=_check_whatsapp_inbound_route,
        admin_url_name="admin:whatsapp_whatsappinboundroute_changelist",
        admin_url_empty_name="admin:whatsapp_whatsappinboundroute_add",
        depends_on="whatsapp.enabled",
    ),
    _StepSpec(
        key="organizations.first_org",
        title="Create the first organisation",
        description=(
            "Every record belongs to an organisation. Create at least one "
            "organisation (add members via Memberships when you are ready)."
        ),
        group="Organizations",
        check=_check_first_organization,
        admin_url_name="admin:organizations_organization_changelist",
        admin_url_empty_name="admin:organizations_organization_add",
    ),
)


@dataclass(frozen=True)
class OnboardingReport:
    steps: list[OnboardingStep] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(1 for step in self.steps if step.required)

    @property
    def completed(self) -> int:
        return sum(1 for step in self.steps if step.required and step.complete)

    @property
    def optional_total(self) -> int:
        return sum(1 for step in self.steps if step.optional)

    @property
    def optional_completed(self) -> int:
        return sum(1 for step in self.steps if step.optional and step.complete)

    @property
    def percent(self) -> int:
        if self.total == 0:
            return 100
        return int(round((self.completed / self.total) * 100))

    @property
    def all_complete(self) -> bool:
        return self.completed >= self.total

    def grouped(self) -> list[tuple[str, list[OnboardingStep]]]:
        seen: list[str] = []
        buckets: dict[str, list[OnboardingStep]] = {}
        for step in self.steps:
            if step.group not in buckets:
                buckets[step.group] = []
                seen.append(step.group)
            buckets[step.group].append(step)
        return [(group, buckets[group]) for group in seen]


class OnboardingService:
    @classmethod
    def get_steps(cls) -> list[OnboardingStep]:
        completion: dict[str, bool] = {}
        for spec in _STEPS:
            try:
                completion[spec.key] = bool(spec.check())
            except Exception:
                completion[spec.key] = False

        steps: list[OnboardingStep] = []
        for spec in _STEPS:
            complete = completion[spec.key]
            blocked_by: str | None = None
            if spec.depends_on and not completion.get(spec.depends_on, False):
                blocked_by = spec.depends_on
            steps.append(
                OnboardingStep(
                    key=spec.key,
                    title=spec.title,
                    description=spec.description,
                    group=spec.group,
                    admin_url=spec.resolve_url(complete=complete),
                    complete=complete,
                    blocked_by=blocked_by,
                    optional=spec.optional,
                ),
            )
        return steps

    @classmethod
    def progress(cls) -> tuple[int, int]:
        report = cls.report()
        return report.completed, report.total

    @classmethod
    def report(cls) -> OnboardingReport:
        return OnboardingReport(steps=cls.get_steps())
