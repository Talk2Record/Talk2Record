from __future__ import annotations

from unittest.mock import patch

import pytest

from talk2record.events.names import RECORD_STORED
from talk2record.notifications.models import Notification
from talk2record.notifications.tasks import handle_domain_event_for_notifications


@pytest.mark.django_db
def test_handle_domain_event_for_notifications_creates_notifications(
    workspace_user, organization
):
    event_payload = {
        "event_id": "notif-test-uuid-001",
        "name": RECORD_STORED,
        "organization_id": organization.pk,
        "user_id": workspace_user.pk,
        "resource_type": "record",
        "resource_id": "1",
        "metadata": {
            "title": "Voice note processed",
            "message": "Record: Oil - 2 x USD 120.00",
            "link_url": "/dashboard/records",
        },
    }

    with patch("talk2record.notifications.services._send_notification_to_user"):
        handle_domain_event_for_notifications(event_payload)

    notification = Notification.objects.filter(
        user=workspace_user,
        type=Notification.Type.RECORD_STORED,
    ).first()
    assert notification is not None
    assert notification.title == "Voice note processed"
    assert notification.message == "Record: Oil - 2 x USD 120.00"
    assert notification.link_url == "/dashboard/records"


@pytest.mark.django_db
def test_handle_domain_event_for_notifications_is_idempotent(
    workspace_user, organization
):
    event_payload = {
        "event_id": "notif-test-uuid-002",
        "name": RECORD_STORED,
        "organization_id": organization.pk,
        "user_id": workspace_user.pk,
        "resource_type": "record",
        "resource_id": "2",
        "metadata": {
            "title": "Record processed",
            "message": "Done",
            "link_url": "/dashboard",
        },
    }

    with patch("talk2record.notifications.services._send_notification_to_user"):
        handle_domain_event_for_notifications(event_payload)
        handle_domain_event_for_notifications(event_payload)

    assert Notification.objects.filter(
        user=workspace_user,
        metadata__event_id="notif-test-uuid-002",
    ).count() == 1


@pytest.mark.django_db
def test_handle_domain_event_for_notifications_skips_non_record_stored(
    workspace_user, organization
):
    event_payload = {
        "event_id": "notif-test-uuid-003",
        "name": "user.registered",
        "organization_id": organization.pk,
        "user_id": workspace_user.pk,
        "resource_type": "user",
        "resource_id": str(workspace_user.pk),
        "metadata": {},
    }

    handle_domain_event_for_notifications(event_payload)

    assert Notification.objects.filter(user=workspace_user).count() == 0


@pytest.mark.django_db
def test_handle_domain_event_for_notifications_fan_out_to_all_active_members(
    organization,
):
    from talk2record.organizations.models import Membership
    from talk2record.users.tests.factories import UserFactory

    user1 = UserFactory.create()
    user2 = UserFactory.create()
    Membership.objects.create(
        user=user1,
        organization=organization,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
    )
    Membership.objects.create(
        user=user2,
        organization=organization,
        role=Membership.Role.ADMIN,
        status=Membership.Status.ACTIVE,
    )

    event_payload = {
        "event_id": "notif-test-uuid-004",
        "name": RECORD_STORED,
        "organization_id": organization.pk,
        "user_id": None,
        "resource_type": "record",
        "resource_id": "99",
        "metadata": {
            "title": "Fan-out test",
            "message": "All members notified",
            "link_url": "/dashboard",
        },
    }

    with patch("talk2record.notifications.services._send_notification_to_user"):
        handle_domain_event_for_notifications(event_payload)

    assert Notification.objects.filter(user=user1, type=Notification.Type.RECORD_STORED).exists()
    assert Notification.objects.filter(user=user2, type=Notification.Type.RECORD_STORED).exists()
