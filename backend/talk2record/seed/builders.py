from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model

from talk2record.analytics.models import DailyMetric
from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.billing.models import Subscription
from talk2record.billing.models import Transaction
from talk2record.integrations.crypto import SecretVault
from talk2record.integrations.models import ApiCredential
from talk2record.integrations.models import Integration
from talk2record.integrations.models import WhatsAppInboundRoute
from talk2record.legal.models import LegalDocumentVersion
from talk2record.legal.models import UserLegalAcceptance
from talk2record.legal.models import UserLegalAttestation
from talk2record.organizations.models import Membership
from talk2record.organizations.models import Organization
from talk2record.records.models import Record
from talk2record.records.services import RecordProcessingService
from talk2record.seed.constants import CUSTOMER_NAMES
from talk2record.seed.constants import PAYMENT_METHODS
from talk2record.seed.constants import PRODUCT_CATALOG
from talk2record.seed.constants import REGIONS
from talk2record.seed.constants import SEED_IP_ADDRESS
from talk2record.seed.constants import SEED_NAMESPACE
from talk2record.seed.constants import SEED_USER_AGENT
from talk2record.seed.constants import TIMEZONES

if TYPE_CHECKING:
    from talk2record.seed.reference_data import ReferenceData
    from talk2record.seed.time_range import SeedTimeRange

User = get_user_model()


@dataclass(slots=True)
class SeedOptions:
    days: int
    months: int
    years: int
    organization_count: int
    users_per_organization: int
    records_per_day: int
    password: str


@dataclass(slots=True)
class SeedSummary:
    counters: dict[str, dict[str, int]] = field(default_factory=dict)

    def bump(
        self,
        bucket: str,
        *,
        created: bool | int = False,
        updated: bool | int = False,
    ) -> None:
        counter = self.counters.setdefault(bucket, {"created": 0, "updated": 0})
        if created:
            counter["created"] += int(created)
        if updated:
            counter["updated"] += int(updated)

    def rows(self) -> list[tuple[str, int, int]]:
        return [
            (bucket, values["created"], values["updated"])
            for bucket, values in sorted(self.counters.items())
            if values["created"] or values["updated"]
        ]


def _apply_timestamp(model, object_id: int, **values) -> None:
    model.objects.filter(pk=object_id).update(**values)


def _first(queryset):
    return queryset.order_by("pk").first()


class SeedWorkspaceBuilder:
    def __init__(
        self,
        *,
        options: SeedOptions,
        reference_data: ReferenceData,
        time_range: SeedTimeRange,
        summary: SeedSummary,
    ) -> None:
        self.options = options
        self.reference_data = reference_data
        self.time_range = time_range
        self.summary = summary

    def build_workspace(self, index: int) -> None:
        organization = self._ensure_organization(index)
        users = self._ensure_workspace_users(index=index, organization=organization)
        owner = users[0]
        self._ensure_integrations(organization=organization, owner=owner)
        self._ensure_subscription(
            organization=organization, owner=owner, plan_index=index - 1,
        )
        record_snapshots = self._ensure_records(organization=organization, users=users)
        self._ensure_daily_metrics(
            organization=organization,
            active_users=len(users),
            record_snapshots=record_snapshots,
        )
        self._ensure_workspace_activity(organization=organization, owner=owner)

    def _ensure_organization(self, index: int) -> Organization:
        slug = f"seed-org-{index:03d}"
        defaults = {
            "name": f"Seed Workspace {index:03d}",
            "region": REGIONS[(index - 1) % len(REGIONS)],
            "timezone": TIMEZONES[(index - 1) % len(TIMEZONES)],
            "default_currency": "USD",
            "status": Organization.Status.ACTIVE,
        }
        organization, created = Organization.objects.update_or_create(
            slug=slug, defaults=defaults,
        )
        self.summary.bump("organizations", created=created, updated=not created)
        return organization

    def _ensure_workspace_users(
        self, *, index: int, organization: Organization,
    ) -> list[User]:
        role_cycle = (
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.OPERATOR,
        )
        users: list[User] = []
        required_signup_versions = [
            version
            for version in self.reference_data.legal_versions.values()
            if version.required_at_signup
        ]
        signup_accepted_at = self.time_range.start_at + timedelta(hours=index)

        for position in range(self.options.users_per_organization):
            role = role_cycle[min(position, len(role_cycle) - 1)]
            user = self._ensure_user(
                email=f"seed-{organization.slug}-{role}@example.com",
                name=f"Seed {organization.name} {role.title()}",
                organization=organization,
            )
            self._ensure_membership(user=user, organization=organization, role=role)
            self._ensure_registration_audit(user=user, organization=organization)
            for version in required_signup_versions:
                self._ensure_legal_acceptance(
                    user=user,
                    document_version=version,
                    source=UserLegalAcceptance.Source.SIGNUP,
                    accepted_at=signup_accepted_at,
                )
            self._ensure_legal_attestation(
                user=user,
                kind=UserLegalAttestation.Kind.VOICE_DATA_CONSENT,
                context=f"{organization.slug}-voice-consent",
                confirmed_at=signup_accepted_at + timedelta(minutes=5 + position),
                metadata={"organization": organization.slug, "role": role},
            )
            self._ensure_legal_attestation(
                user=user,
                kind=UserLegalAttestation.Kind.AI_OUTPUT_REVIEW,
                context=f"{organization.slug}-ai-review",
                confirmed_at=signup_accepted_at + timedelta(minutes=15 + position),
                metadata={"organization": organization.slug, "role": role},
            )
            users.append(user)

        return users

    def _ensure_user(
        self, *, email: str, name: str, organization: Organization,
    ) -> User:
        user = User.objects.filter(email=email).first()
        created = user is None
        if user is None:
            user = User.objects.create_user(
                email=email,
                password=self.options.password,
                name=name,
            )
        else:
            user.name = name
            user.onboarding_completed = True
            user.current_organization = organization
            user.save(
                update_fields=[
                    "name",
                    "onboarding_completed",
                    "current_organization",
                ],
            )

        user.name = name
        user.onboarding_completed = True
        user.current_organization = organization
        user.set_password(self.options.password)
        user.save(
            update_fields=[
                "name",
                "password",
                "onboarding_completed",
                "current_organization",
            ],
        )
        self.summary.bump("users", created=created, updated=not created)
        return user

    def _ensure_membership(
        self,
        *,
        user: User,
        organization: Organization,
        role: str,
    ) -> Membership:
        membership, created = Membership.objects.update_or_create(
            user=user,
            organization=organization,
            defaults={
                "role": role,
                "status": Membership.Status.ACTIVE,
            },
        )
        self.summary.bump("memberships", created=created, updated=not created)
        return membership

    def _ensure_registration_audit(
        self, *, user: User, organization: Organization,
    ) -> None:
        registered_at = self.time_range.start_at + timedelta(minutes=user.pk or 0)
        self._ensure_audit_log(
            action="user.registered",
            resource_type="user",
            resource_id=str(user.pk),
            actor=user,
            organization=organization,
            created_at=registered_at,
            metadata={"documents_seeded": True, "seed_user": user.email},
        )

    def _ensure_integrations(self, *, organization: Organization, owner: User) -> None:
        whatsapp = self.reference_data.integrations["whatsapp"]
        stripe = self.reference_data.integrations["stripe"]
        ai = self.reference_data.integrations["ai"]

        self._ensure_api_credential(
            integration=whatsapp,
            plain_secret="seed-global-whatsapp-secret",
        )
        self._ensure_api_credential(
            integration=stripe,
            plain_secret="seed-global-stripe-secret",
        )
        self._ensure_api_credential(
            integration=ai,
            plain_secret="seed-global-ai-secret",
        )
        self._ensure_whatsapp_route(organization=organization)
        self._ensure_legal_attestation(
            user=owner,
            kind=UserLegalAttestation.Kind.WHATSAPP_PERMISSION,
            context=f"{organization.slug}-whatsapp-permission",
            confirmed_at=self.time_range.start_at + timedelta(days=1),
            metadata={"integration": "whatsapp", "organization": organization.slug},
        )
        self._ensure_audit_log(
            action="integration.tested",
            resource_type="integration",
            resource_id=f"{organization.slug}:whatsapp",
            actor=owner,
            organization=organization,
            created_at=self.time_range.end_at - timedelta(hours=1),
            metadata={"integration": "whatsapp", "status": "connected"},
        )
        self._ensure_event(
            name="integration_connected",
            category="integrations",
            organization=organization,
            seed_key=f"integration-connected:{organization.slug}:whatsapp",
            occurred_at=self.time_range.end_at - timedelta(hours=1),
            properties={"integration": "whatsapp", "status": "connected"},
        )

    def _ensure_api_credential(
        self,
        *,
        integration: Integration,
        plain_secret: str,
    ) -> ApiCredential:
        credential, created = ApiCredential.objects.update_or_create(
            integration=integration,
            defaults={
                "encrypted_secret": SecretVault.encrypt(plain_secret),
            },
        )
        self.summary.bump("api_credentials", created=created, updated=not created)
        return credential

    def _ensure_whatsapp_route(self, *, organization: Organization) -> WhatsAppInboundRoute:
        route, created = WhatsAppInboundRoute.objects.update_or_create(
            organization=organization,
            defaults={"phone_number_id": f"seed-wa-{organization.slug}"},
        )
        self.summary.bump("whatsapp_routes", created=created, updated=not created)
        return route

    def _ensure_subscription(
        self,
        *,
        organization: Organization,
        owner: User,
        plan_index: int,
    ) -> Subscription:
        plan_codes = tuple(self.reference_data.plans)
        plan = self.reference_data.plans[plan_codes[plan_index % len(plan_codes)]]
        subscription, created = Subscription.objects.update_or_create(
            organization=organization,
            provider_subscription_id=f"seed-subscription-{organization.slug}",
            defaults={
                "plan": plan,
                "provider": Subscription.Provider.STRIPE,
                "status": Subscription.Status.ACTIVE,
                "currency": plan.currency,
                "amount": plan.base_price,
                "seats": self.options.users_per_organization,
                "current_period_end": self.time_range.end_at + timedelta(days=30),
                "canceled_at": None,
            },
        )
        self.summary.bump("subscriptions", created=created, updated=not created)
        billing_policy = self.reference_data.legal_versions[
            LegalDocumentVersion.DocumentKey.BILLING_POLICY
        ]
        self._ensure_legal_acceptance(
            user=owner,
            document_version=billing_policy,
            source=UserLegalAcceptance.Source.FEATURE_GATE,
            accepted_at=self.time_range.start_at + timedelta(days=2),
        )
        self._ensure_legal_attestation(
            user=owner,
            kind=UserLegalAttestation.Kind.BILLING_AUTORENEWAL,
            context=f"{organization.slug}-billing-renewal",
            confirmed_at=self.time_range.start_at + timedelta(days=2, minutes=5),
            metadata={"plan": plan.code, "organization": organization.slug},
        )
        self._ensure_audit_log(
            action="billing.checkout.started",
            resource_type="plan",
            resource_id=str(plan.pk),
            actor=owner,
            organization=organization,
            created_at=self.time_range.start_at + timedelta(days=2, minutes=10),
            metadata={"provider": Subscription.Provider.STRIPE, "plan": plan.code},
        )
        self._ensure_event(
            name="billing_checkout_started",
            category="billing",
            organization=organization,
            seed_key=f"billing-start:{organization.slug}",
            occurred_at=self.time_range.start_at + timedelta(days=2, minutes=10),
            properties={"plan": plan.code, "provider": Subscription.Provider.STRIPE},
        )

        for month_index, period_start in enumerate(self._month_start_datetimes()):
            self._ensure_transaction(
                subscription=subscription,
                period_start=period_start,
                amount=plan.base_price,
                sequence=month_index,
            )

        return subscription

    def _ensure_transaction(
        self,
        *,
        subscription: Subscription,
        period_start: datetime,
        amount: Decimal,
        sequence: int,
    ) -> Transaction:
        provider_transaction_id = (
            f"seed-txn-{subscription.organization.slug}-{period_start:%Y%m}"
        )
        transaction, created = Transaction.objects.update_or_create(
            provider_transaction_id=provider_transaction_id,
            defaults={
                "subscription": subscription,
                "amount": amount,
                "currency": subscription.currency,
                "status": Transaction.Status.PAID,
                "invoice_number": (
                    f"INV-{subscription.organization.slug.upper()}-{period_start:%Y%m}"
                ),
                "issued_at": period_start,
                "paid_at": period_start + timedelta(hours=6),
                "raw_payload": {
                    "seed_namespace": SEED_NAMESPACE,
                    "sequence": sequence,
                    "organization": subscription.organization.slug,
                },
            },
        )
        self.summary.bump("transactions", created=created, updated=not created)
        return transaction

    def _ensure_records(
        self, *, organization: Organization, users: list[User],
    ) -> list[dict[str, object]]:
        snapshots: list[dict[str, object]] = []
        for current_date in self.time_range.iter_dates():
            for sequence in range(self.options.records_per_day):
                occurred_at = self.time_range.at_slot(
                    current_date,
                    slot=sequence,
                    total_slots=self.options.records_per_day,
                )
                user = users[sequence % len(users)]
                status_selector = (current_date.toordinal() + sequence) % 6
                if status_selector == 0:
                    desired_status = Record.Status.FAILED
                elif status_selector == 1:
                    desired_status = Record.Status.REVIEW
                else:
                    desired_status = Record.Status.STORED
                amount = (
                    Decimal("35.00") + Decimal(sequence * 7) + Decimal(current_date.day)
                )
                record = self._ensure_record(
                    organization=organization,
                    user=user,
                    occurred_at=occurred_at,
                    sequence=sequence,
                    desired_status=desired_status,
                    amount=amount,
                )
                snapshots.append(
                    {
                        "date": current_date,
                        "status": record.status,
                        "amount": amount,
                    },
                )

        return snapshots

    def _ensure_record(  # noqa: PLR0913
        self,
        *,
        organization: Organization,
        user: User,
        occurred_at: datetime,
        sequence: int,
        desired_status: str,
        amount: Decimal,
    ) -> Record:
        source_reference = (
            f"seed-{organization.slug}-{occurred_at:%Y%m%d}-{sequence + 1:02d}"
        )
        customer_name = CUSTOMER_NAMES[
            (sequence + occurred_at.day) % len(CUSTOMER_NAMES)
        ]
        product = PRODUCT_CATALOG[(sequence + occurred_at.month) % len(PRODUCT_CATALOG)]
        payment_method = PAYMENT_METHODS[
            (sequence + occurred_at.weekday()) % len(PAYMENT_METHODS)
        ]
        from talk2record.ai.services.extraction import ExtractionService
        from talk2record.ai.services.transcription import TranscriptionService

        extraction_hint = {
            "customer_name": customer_name,
            "product": product,
            "quantity": sequence + 1,
            "amount": str(amount),
            "currency": organization.default_currency,
            "payment_method": payment_method,
        }
        audio_url = f"https://media.example.com/{source_reference}.mp3"
        lookup = {"organization": organization, "source_reference": source_reference}
        record = _first(Record.objects.filter(**lookup))
        created = record is None
        if record is None:
            record = Record.objects.create(
                organization=organization,
                created_by=user,
                source=Record.Source.WHATSAPP,
                type=Record.Type.VOICE_NOTE,
                source_reference=source_reference,
                audio_url=audio_url,
            )
        else:
            record.created_by = user
            record.source = Record.Source.WHATSAPP
            record.audio_url = audio_url
            record.save(update_fields=["created_by", "source", "audio_url", "updated_at"])

        # Seed transcript and extraction artifacts
        transcript_result = TranscriptionService.transcribe(record)
        RecordProcessingService.save_transcript_artifact(record, transcript_result)

        if desired_status in {Record.Status.REVIEW, Record.Status.STORED}:
            extraction_result = ExtractionService.extract(
                transcript=RecordProcessingService.get_transcript(record),
                context=extraction_hint,
            )
            RecordProcessingService.save_extraction_artifact(record, extraction_result)

        if desired_status == Record.Status.STORED:
            was_stored = record.status == Record.Status.STORED
            record.processing_error = ""
            record.save(update_fields=["processing_error", "updated_at"])
            if not was_stored:
                RecordProcessingService.store(record)
        elif desired_status == Record.Status.REVIEW:
            self._ensure_event(
                name="record_review_pending",
                category="records",
                organization=organization,
                seed_key=f"record-review:{source_reference}",
                occurred_at=occurred_at + timedelta(minutes=3),
                properties={"recordId": record.pk, "source": record.source},
            )
        else:
            record.status = Record.Status.FAILED
            record.processing_error = "Seeded speech-to-text retry required."
            record.save(
                update_fields=[
                    "status",
                    "processing_error",
                    "updated_at",
                ],
            )
            self._ensure_event(
                name="record_processing_failed",
                category="records",
                organization=organization,
                seed_key=f"record-failed:{source_reference}",
                occurred_at=occurred_at + timedelta(minutes=2),
                properties={"recordId": record.pk, "source": record.source},
            )

        _apply_timestamp(
            Record,
            record.pk,
            created_at=occurred_at,
            updated_at=occurred_at + timedelta(minutes=5),
        )
        record.refresh_from_db()
        self.summary.bump("records", created=created, updated=not created)
        return record

    def _ensure_daily_metrics(
        self,
        *,
        organization: Organization,
        active_users: int,
        record_snapshots: list[dict[str, object]],
    ) -> None:
        records_by_date: dict[object, list[dict[str, object]]] = {}
        for snapshot in record_snapshots:
            records_by_date.setdefault(snapshot["date"], []).append(snapshot)

        for metric_date, snapshots in records_by_date.items():
            stored_snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot["status"] == Record.Status.STORED
            ]
            metric, created = DailyMetric.objects.update_or_create(
                organization=organization,
                metric_date=metric_date,
                defaults={
                    "voice_processed": len(snapshots),
                    "records_created": len(stored_snapshots),
                    "revenue": sum(
                        (snapshot["amount"] for snapshot in stored_snapshots),
                        Decimal("0.00"),
                    ),
                    "feature_usage": len(stored_snapshots) + 2,
                    "active_users": active_users,
                },
            )
            _apply_timestamp(
                DailyMetric,
                metric.pk,
                created_at=self.time_range.at_slot(metric_date, slot=0, total_slots=1),
            )
            self.summary.bump("daily_metrics", created=created, updated=not created)

    def _ensure_workspace_activity(
        self, *, organization: Organization, owner: User,
    ) -> None:
        for offset, current_date in enumerate(self.time_range.iter_dates()[::7]):
            occurred_at = self.time_range.at_slot(current_date, slot=0, total_slots=1)
            self._ensure_event(
                name="dashboard_viewed",
                category="analytics",
                organization=organization,
                seed_key=f"dashboard-viewed:{organization.slug}:{offset}",
                occurred_at=occurred_at,
                properties={"organization": organization.slug, "viewer": owner.email},
            )

    def _ensure_legal_acceptance(
        self,
        *,
        user: User,
        document_version: LegalDocumentVersion,
        source: str,
        accepted_at: datetime,
    ) -> UserLegalAcceptance:
        acceptance = _first(
            UserLegalAcceptance.objects.filter(
                user=user,
                document_version=document_version,
                acceptance_source=source,
            ),
        )
        created = acceptance is None
        if acceptance is None:
            acceptance = UserLegalAcceptance.objects.create(
                user=user,
                document_version=document_version,
                acceptance_source=source,
                ip_address=SEED_IP_ADDRESS,
                user_agent=SEED_USER_AGENT,
            )
        else:
            acceptance.ip_address = SEED_IP_ADDRESS
            acceptance.user_agent = SEED_USER_AGENT
            acceptance.save(update_fields=["ip_address", "user_agent"])

        _apply_timestamp(
            UserLegalAcceptance,
            acceptance.pk,
            accepted_at=accepted_at,
        )
        latest_accepted_at = (
            UserLegalAcceptance.objects.filter(user=user)
            .order_by("-accepted_at")
            .first()
        )
        if latest_accepted_at is not None:
            user.latest_required_legal_acceptance_at = latest_accepted_at.accepted_at
            user.save(update_fields=["latest_required_legal_acceptance_at"])
        self.summary.bump("legal_acceptances", created=created, updated=not created)
        return acceptance

    def _ensure_legal_attestation(
        self,
        *,
        user: User,
        kind: str,
        context: str,
        confirmed_at: datetime,
        metadata: dict[str, object],
    ) -> UserLegalAttestation:
        attestation = _first(
            UserLegalAttestation.objects.filter(
                user=user,
                kind=kind,
                context=context,
            ),
        )
        created = attestation is None
        if attestation is None:
            attestation = UserLegalAttestation.objects.create(
                user=user,
                kind=kind,
                context=context,
                metadata={"seed_namespace": SEED_NAMESPACE, **metadata},
                ip_address=SEED_IP_ADDRESS,
                user_agent=SEED_USER_AGENT,
            )
        else:
            attestation.metadata = {"seed_namespace": SEED_NAMESPACE, **metadata}
            attestation.ip_address = SEED_IP_ADDRESS
            attestation.user_agent = SEED_USER_AGENT
            attestation.confirmed = True
            attestation.save(
                update_fields=[
                    "metadata",
                    "ip_address",
                    "user_agent",
                    "confirmed",
                ],
            )

        _apply_timestamp(
            UserLegalAttestation,
            attestation.pk,
            confirmed_at=confirmed_at,
        )
        self.summary.bump("legal_attestations", created=created, updated=not created)
        return attestation

    def _ensure_audit_log(  # noqa: PLR0913
        self,
        *,
        action: str,
        resource_type: str,
        resource_id: str,
        actor,
        organization,
        created_at: datetime,
        metadata: dict[str, object],
    ) -> AuditLog:
        audit_log = _first(
            AuditLog.objects.filter(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                organization=organization,
            ),
        )
        created = audit_log is None
        payload = {"seed_namespace": SEED_NAMESPACE, **metadata}
        if audit_log is None:
            audit_log = AuditLog.objects.create(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                actor=actor,
                organization=organization,
                metadata=payload,
            )
        else:
            audit_log.actor = actor
            audit_log.metadata = payload
            audit_log.save(update_fields=["actor", "metadata"])

        _apply_timestamp(AuditLog, audit_log.pk, created_at=created_at)
        self.summary.bump("audit_logs", created=created, updated=not created)
        return audit_log

    def _ensure_event(  # noqa: PLR0913
        self,
        *,
        name: str,
        category: str,
        organization: Organization,
        seed_key: str,
        occurred_at: datetime,
        properties: dict[str, object],
    ) -> Event:
        event = None
        for candidate in Event.objects.filter(
            name=name,
            category=category,
            organization=organization,
        ).order_by("pk"):
            if candidate.properties.get("seed_key") == seed_key:
                event = candidate
                break

        created = event is None
        payload = {
            "seed_key": seed_key,
            "seed_namespace": SEED_NAMESPACE,
            **properties,
        }
        if event is None:
            event = Event.objects.create(
                name=name,
                category=category,
                organization=organization,
                properties=payload,
            )
        else:
            event.properties = payload
            event.save(update_fields=["properties"])

        _apply_timestamp(Event, event.pk, created_at=occurred_at)
        self.summary.bump("events", created=created, updated=not created)
        return event

    def _month_start_datetimes(self) -> list[datetime]:
        month_start_dates: list[datetime] = []
        seen_months: set[tuple[int, int]] = set()
        for value in self.time_range.iter_dates():
            month_key = (value.year, value.month)
            if month_key in seen_months:
                continue
            seen_months.add(month_key)
            month_start_dates.append(
                self.time_range.at_slot(value, slot=0, total_slots=1),
            )
        return month_start_dates
