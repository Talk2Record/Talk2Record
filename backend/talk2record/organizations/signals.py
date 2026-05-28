"""
Signals for organization-related events.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from talk2record.notifications.services import NotificationService
from talk2record.organizations.models import Membership


@receiver(post_save, sender=Membership)
def notify_membership_created(
    sender,
    instance: Membership,
    created: bool,  # noqa: FBT001
    **kwargs,
) -> None:
    """Notify user when they are added to an organization (invite scenario)."""
    if not created:
        return
    # Skip first member: registration flow creates the user's own org
    if instance.organization.memberships.count() <= 1:
        return
    NotificationService.create(
        user=instance.user,
        notification_type="membership_invite",
        title=f"You were added to {instance.organization.name}",
        message=f"You can now access {instance.organization.name} workspace.",
        organization=instance.organization,
        metadata={"membership_id": instance.pk},
    )
