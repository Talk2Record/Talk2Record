from http import HTTPStatus
from decimal import Decimal

import pytest
from celery.result import EagerResult
from django.urls import reverse

from talk2record.analytics.models import Event
from talk2record.audit.models import AuditLog
from talk2record.records.models import Record
from talk2record.records.services import RecordProcessingService
from talk2record.records.tasks import extract_structured_data
from talk2record.records.tasks import store_record
from talk2record.records.tasks import transcribe_voice


@pytest.mark.django_db
def test_record_str(record):
    assert str(record) == f"{record.organization.name}: {record.customer_name}"


@pytest.mark.django_db
def test_record_processing_service_updates_status(record):
    record.amount = Decimal("0.00")
    record.confidence_score = Decimal("0.000")
    record.voice_transcript = ""
    record.save()

    transcribed = RecordProcessingService.transcribe(record)
    reviewed = RecordProcessingService.extract_structured_data(transcribed)
    stored = RecordProcessingService.store(reviewed)

    stored.refresh_from_db()
    assert "Structured transcript placeholder" in stored.voice_transcript
    assert reviewed.confidence_score == Decimal("0.950")
    assert stored.status == Record.Status.STORED
    assert AuditLog.objects.filter(action="record.stored").exists()
    assert Event.objects.filter(name="record_stored").exists()


@pytest.mark.django_db
def test_record_tasks(settings, record):
    settings.CELERY_TASK_ALWAYS_EAGER = True

    transcribe_result = transcribe_voice.delay(record.pk)
    extract_result = extract_structured_data.delay(record.pk)
    store_result = store_record.delay(record.pk)

    record.refresh_from_db()
    assert isinstance(transcribe_result, EagerResult)
    assert isinstance(extract_result, EagerResult)
    assert isinstance(store_result, EagerResult)
    assert record.status == Record.Status.STORED


@pytest.mark.django_db
def test_record_admin_page(admin_client, record):
    response = admin_client.get(reverse("admin:records_record_changelist"))

    assert response.status_code == HTTPStatus.OK
