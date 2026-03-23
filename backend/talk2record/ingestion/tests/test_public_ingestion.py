from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.audit.models import AuditLog
from talk2record.organizations.services import OrganizationAPIKeyService
from talk2record.records.models import Record


@pytest.mark.django_db
class TestPublicRecordIngestion:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    @pytest.fixture(autouse=True)
    def clear_throttle_cache(self):
        cache.clear()

    def test_requires_valid_api_key(self, api_client: APIClient):
        response = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "Kifaru"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accepts_with_org_api_key_and_queues_processing(
        self,
        monkeypatch: pytest.MonkeyPatch,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        queued: list[tuple[int, str, str]] = []
        api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Public ingestion key",
            created_by=workspace_user,
        )

        def fake_delay(record_id: int, payload_id: int | None = None, **kwargs):
            del payload_id
            queued.append(
                (
                    record_id,
                    str(kwargs.get("request_id", "")),
                    str(kwargs.get("event_id", "")),
                ),
            )

        monkeypatch.setattr(
            "talk2record.ingestion.views.process_whatsapp_record.delay",
            fake_delay,
        )

        response = api_client.post(
            reverse("api-public-ingestion-records"),
            data={
                "sourceReference": "public-msg-1",
                "customerName": "Kifaru",
                "product": "Rice",
                "quantity": 3,
                "amount": "120.00",
                "currency": "kes",
                "audioUrl": "https://example.com/audio.ogg",
            },
            format="json",
            HTTP_X_API_KEY=raw_key,
            HTTP_X_REQUEST_ID="req-public-1",
        )

        record = Record.objects.get(
            source=Record.Source.API,
            source_reference="public-msg-1",
        )
        api_key.refresh_from_db()
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data["status"] == "accepted"
        assert response.data["recordId"] == record.pk
        assert record.organization_id == organization.pk
        assert record.created_by_id == workspace_user.pk
        # Currency hint stored as artifact, not on Record directly
        hint = record.artifacts.get(key="extraction_hint")
        assert hint.content["currency"] == "KES"
        assert queued == [(record.pk, "req-public-1", queued[0][2])]
        assert queued[0][2]
        assert api_key.last_used_at is not None
        assert api_key.last_used_ip == "127.0.0.1"
        assert AuditLog.objects.filter(
            action="organization.api_key.used",
            resource_type="organization_api_key",
            resource_id=str(api_key.pk),
            metadata__path="/api/public/ingestion/records/",
            metadata__method="POST",
        ).exists()

    def test_duplicate_source_reference_returns_duplicate(
        self,
        monkeypatch: pytest.MonkeyPatch,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        _api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Duplicate test key",
            created_by=workspace_user,
        )
        queued: list[int] = []
        monkeypatch.setattr(
            "talk2record.ingestion.views.process_whatsapp_record.delay",
            lambda record_id, *args, **kwargs: queued.append(record_id),
        )

        first = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"sourceReference": "dup-1", "customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        second = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"sourceReference": "dup-1", "customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )

        assert first.status_code == status.HTTP_202_ACCEPTED
        assert second.status_code == status.HTTP_200_OK
        assert second.data["status"] == "duplicate"
        assert Record.objects.filter(
            source=Record.Source.API,
            source_reference="dup-1",
        ).count() == 1
        assert len(queued) == 1

    def test_rejects_key_without_ingestion_scope(
        self,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        _api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Read only key",
            scopes=["records:read"],
            created_by=workspace_user,
        )

        response = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rejects_expired_key(
        self,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Expired key",
            created_by=workspace_user,
        )
        api_key.expires_at = timezone.now() - timedelta(minutes=1)
        api_key.save(update_fields=["expires_at", "updated_at"])

        response = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_enforces_per_key_rate_limit_override(
        self,
        monkeypatch: pytest.MonkeyPatch,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        _api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Rate limited key",
            created_by=workspace_user,
            rate_limit_per_minute=1,
        )
        monkeypatch.setattr(
            "talk2record.ingestion.views.process_whatsapp_record.delay",
            lambda *args, **kwargs: None,
        )

        first = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        second = api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "Kifaru"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )

        assert first.status_code == status.HTTP_202_ACCEPTED
        assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_api_key_used_audit_is_sampled(
        self,
        settings,
        monkeypatch: pytest.MonkeyPatch,
        organization,
        workspace_user,
        api_client: APIClient,
    ):
        settings.AUDIT_API_KEY_USED_SAMPLE_INTERVAL_MINUTES = 5
        _api_key, raw_key = OrganizationAPIKeyService.create_key(
            organization=organization,
            name="Sampled key",
            created_by=workspace_user,
        )
        monkeypatch.setattr(
            "talk2record.ingestion.views.process_whatsapp_record.delay",
            lambda *args, **kwargs: None,
        )

        api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "A", "sourceReference": "s1"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )
        api_client.post(
            reverse("api-public-ingestion-records"),
            data={"customerName": "B", "sourceReference": "s2"},
            format="json",
            HTTP_X_API_KEY=raw_key,
        )

        used_count = AuditLog.objects.filter(
            action="organization.api_key.used",
            resource_type="organization_api_key",
        ).count()
        assert used_count == 1
