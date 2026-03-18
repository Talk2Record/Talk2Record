from celery import shared_task

from talk2record.records.models import Record
from talk2record.records.services import RecordProcessingService


@shared_task
def transcribe_voice(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    RecordProcessingService.transcribe(record)


@shared_task
def extract_structured_data(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    RecordProcessingService.extract_structured_data(record)


@shared_task
def store_record(record_id: int) -> None:
    record = Record.objects.get(pk=record_id)
    RecordProcessingService.store(record)
