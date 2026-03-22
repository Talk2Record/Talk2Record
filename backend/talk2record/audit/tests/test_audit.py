from http import HTTPStatus
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from talk2record.audit.models import AuditLog
from talk2record.audit.services import AuditService


@pytest.mark.django_db
def test_audit_log_str(workspace_user, organization):
    log = AuditService.log(
        action="user.registered",
        resource_type="user",
        resource_id=str(workspace_user.pk),
        actor=workspace_user,
        organization=organization,
        metadata={"source": "pytest"},
    )

    assert str(log) == "user.registered"
    assert log.metadata == {"source": "pytest"}


@pytest.mark.django_db
def test_audit_admin_page(admin_client, workspace_user, organization):
    AuditService.log(
        action="user.registered",
        resource_type="user",
        resource_id=str(workspace_user.pk),
        actor=workspace_user,
        organization=organization,
    )

    response = admin_client.get(reverse("admin:audit_auditlog_changelist"))

    assert response.status_code == HTTPStatus.OK


@pytest.mark.django_db
def test_log_api_key_used_if_sampled_respects_interval(workspace_user, organization, settings):
    settings.AUDIT_API_KEY_USED_SAMPLE_INTERVAL_MINUTES = 5
    a = AuditService.log_api_key_used_if_sampled(
        api_key_id=1,
        actor=workspace_user,
        organization=organization,
        metadata={"path": "/test"},
    )
    assert a is not None
    assert AuditLog.objects.filter(action=AuditService.ACTION_API_KEY_USED).count() == 1

    b = AuditService.log_api_key_used_if_sampled(
        api_key_id=1,
        actor=workspace_user,
        organization=organization,
        metadata={"path": "/test2"},
    )
    assert b is None
    assert AuditLog.objects.filter(action=AuditService.ACTION_API_KEY_USED).count() == 1


@pytest.mark.django_db
def test_log_api_key_used_zero_interval_logs_every_time(workspace_user, organization, settings):
    settings.AUDIT_API_KEY_USED_SAMPLE_INTERVAL_MINUTES = 0
    a = AuditService.log_api_key_used_if_sampled(
        api_key_id=2,
        actor=workspace_user,
        organization=organization,
        metadata={"path": "/test"},
    )
    b = AuditService.log_api_key_used_if_sampled(
        api_key_id=2,
        actor=workspace_user,
        organization=organization,
        metadata={"path": "/test2"},
    )
    assert a is not None
    assert b is not None
    assert AuditLog.objects.filter(action=AuditService.ACTION_API_KEY_USED).count() == 2


@pytest.mark.django_db
def test_prune_audit_logs_command(workspace_user, organization):
    log = AuditService.log(
        action=AuditService.ACTION_API_KEY_USED,
        resource_type=AuditService.RESOURCE_TYPE_API_KEY,
        resource_id="1",
        actor=workspace_user,
        organization=organization,
    )
    AuditLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timedelta(days=100),
    )

    call_command("prune_audit_logs", "--days=90")

    assert not AuditLog.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
def test_prune_audit_logs_dry_run(workspace_user, organization):
    log = AuditService.log(
        action=AuditService.ACTION_API_KEY_USED,
        resource_type=AuditService.RESOURCE_TYPE_API_KEY,
        resource_id="1",
        actor=workspace_user,
        organization=organization,
    )
    AuditLog.objects.filter(pk=log.pk).update(
        created_at=timezone.now() - timedelta(days=100),
    )

    call_command("prune_audit_logs", "--days=90", "--dry-run")

    assert AuditLog.objects.filter(pk=log.pk).exists()
