from http import HTTPStatus

import pytest
from django.urls import reverse

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
