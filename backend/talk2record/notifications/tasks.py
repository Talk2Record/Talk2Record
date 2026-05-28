from __future__ import annotations

from celery import shared_task

from talk2record.events.decorators import already_handled
from talk2record.events.names import MEMBERSHIP_ACCEPTED
from talk2record.events.names import MEMBERSHIP_INVITED
from talk2record.events.names import RECORD_STORED
from talk2record.notifications.models import Notification
from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import MembershipInvitation
from talk2record.organizations.models import Organization


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def handle_domain_event_for_notifications(self, event_payload: dict) -> None:
    if already_handled(event_payload, "notifications"):
        return

    event_name = str(event_payload.get("name", ""))
    if event_name == RECORD_STORED:
        _handle_record_stored(event_payload)
        return
    if event_name == MEMBERSHIP_INVITED:
        _handle_membership_invited(event_payload)
        return
    if event_name == MEMBERSHIP_ACCEPTED:
        _handle_membership_accepted(event_payload)
        return


def _handle_record_stored(event_payload: dict) -> None:
    event_id = str(event_payload.get("event_id", ""))
    organization_id = event_payload.get("organization_id")
    organization = Organization.objects.filter(pk=organization_id).first()
    if organization is None:
        return

    metadata = dict(event_payload.get("metadata") or {})
    title = str(metadata.get("title") or "Record processed")
    message = str(metadata.get("message") or "")
    link_url = str(metadata.get("link_url") or "/dashboard/records")
    resource_id = event_payload.get("resource_id")

    memberships = organization.memberships.filter(
        status=Membership.Status.ACTIVE,
    ).select_related("user")
    for membership in memberships:
        NotificationService.create(
            user=membership.user,
            notification_type=Notification.Type.RECORD_STORED,
            title=title,
            message=message,
            link_url=link_url,
            organization=organization,
            metadata={"record_id": resource_id, "event_id": event_id},
        )


def _handle_membership_invited(event_payload: dict) -> None:
    """Notify existing admins that an invitation was issued."""
    resource_id = event_payload.get("resource_id")
    if not resource_id:
        return
    invitation = (
        MembershipInvitation.objects.select_related("organization")
        .filter(pk=resource_id)
        .first()
    )
    if invitation is None:
        return
    admin_memberships = invitation.organization.memberships.filter(
        role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        status=Membership.Status.ACTIVE,
    ).select_related("user")
    for membership in admin_memberships:
        NotificationService.create(
            user=membership.user,
            notification_type=Notification.Type.MEMBERSHIP_INVITE,
            title=f"Invitation sent to {invitation.email}",
            message=f"Role: {invitation.role}",
            link_url="/dashboard/team",
            organization=invitation.organization,
            metadata={"invitation_id": invitation.pk},
        )


def _handle_membership_accepted(event_payload: dict) -> None:
    resource_id = event_payload.get("resource_id")
    if not resource_id:
        return
    membership = (
        Membership.objects.select_related("organization", "user")
        .filter(pk=resource_id)
        .first()
    )
    if membership is None:
        return
    NotificationService.create(
        user=membership.user,
        notification_type=Notification.Type.MEMBERSHIP_INVITE,
        title=f"You joined {membership.organization.name}",
        message="You can now access this workspace.",
        link_url="/dashboard",
        organization=membership.organization,
        metadata={"membership_id": membership.pk},
    )
    admin_memberships = (
        membership.organization.memberships.filter(
            role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
            status=Membership.Status.ACTIVE,
        )
        .exclude(pk=membership.pk)
        .select_related("user")
    )
    for admin in admin_memberships:
        NotificationService.create(
            user=admin.user,
            notification_type=Notification.Type.MEMBERSHIP_INVITE,
            title=f"{membership.user.email} joined the team",
            message=f"Role: {membership.role}",
            link_url="/dashboard/team",
            organization=membership.organization,
            metadata={"membership_id": membership.pk},
        )
