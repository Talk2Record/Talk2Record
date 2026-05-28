from __future__ import annotations

from celery import current_app
from celery import shared_task
from django.utils.module_loading import import_string

from talk2record.events.bus import EventBus


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def dispatch_domain_event(self, event_payload: dict) -> None:
    task_names = EventBus.get_handlers(str(event_payload.get("name", "")))
    for task_name in task_names:
        task = current_app.tasks.get(task_name)
        if task is None:
            try:
                task = import_string(task_name)
            except ImportError:
                task = None

        if task is not None:
            task.delay(event_payload)
        else:
            current_app.send_task(task_name, args=[event_payload])

    event_id = event_payload.get("event_id")
    if event_id:
        from talk2record.events.models import DomainEvent as DomainEventRecord

        DomainEventRecord.objects.filter(id=event_id).update(processed=True)
