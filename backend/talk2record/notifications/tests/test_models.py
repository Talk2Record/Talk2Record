from __future__ import annotations

import pytest
from django.utils import timezone

from talk2record.notifications.models import Notification


@pytest.mark.django_db
def test_notification_str(workspace_user, organization):
    notification = Notification.objects.create(
        user=workspace_user,
        organization=organization,
        type=Notification.Type.RECORD_STORED,
        title="Test notification",
    )
    assert str(notification) == "record_stored: Test notification"


@pytest.mark.django_db
def test_notification_field_defaults(workspace_user):
    notification = Notification.objects.create(
        user=workspace_user,
        type=Notification.Type.GENERAL,
        title="Hello",
    )
    assert notification.message == ""
    assert notification.link_url == ""
    assert notification.read_at is None
    assert notification.metadata == {}
    assert notification.organization is None


@pytest.mark.django_db
def test_notification_read_at_update(workspace_user):
    notification = Notification.objects.create(
        user=workspace_user,
        type=Notification.Type.GENERAL,
        title="To be read",
    )
    assert notification.read_at is None
    now = timezone.now()
    notification.read_at = now
    notification.save(update_fields=["read_at"])
    notification.refresh_from_db()
    assert notification.read_at is not None


@pytest.mark.django_db
def test_notification_ordering_newest_first(workspace_user):
    n1 = Notification.objects.create(
        user=workspace_user, type=Notification.Type.GENERAL, title="First"
    )
    n2 = Notification.objects.create(
        user=workspace_user, type=Notification.Type.GENERAL, title="Second"
    )
    qs = list(Notification.objects.filter(user=workspace_user))
    assert qs[0].pk == n2.pk
    assert qs[1].pk == n1.pk
