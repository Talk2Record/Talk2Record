from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        PAST_DUE = "past_due", _("Past due")
        SUSPENDED = "suspended", _("Suspended")

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    region = models.CharField(max_length=64, blank=True)
    timezone = models.CharField(max_length=64, default="UTC")
    default_currency = models.CharField(max_length=8, default="USD")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Membership(models.Model):
    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        ADMIN = "admin", _("Admin")
        OPERATOR = "operator", _("Operator")

    class Status(models.TextChoices):
        ACTIVE = "active", _("Active")
        INVITED = "invited", _("Invited")
        SUSPENDED = "suspended", _("Suspended")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.OPERATOR)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.ACTIVE)
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_membership_per_user_org",
            ),
        ]
        ordering = ["organization__name", "user__email"]

    def __str__(self) -> str:
        return f"{self.user.email} -> {self.organization.name}"


class MembershipInvitation(models.Model):
    """Pending invitation for a user to join an organization.

    The invitation is consumed by a short-lived signed token; only a ``token_hash``
    is persisted so the raw token is usable exactly once (it is emailed to the
    invitee by the invitation service at creation time).
    """

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        ACCEPTED = "accepted", _("Accepted")
        REVOKED = "revoked", _("Revoked")
        EXPIRED = "expired", _("Expired")

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField()
    role = models.CharField(
        max_length=32,
        choices=Membership.Role.choices,
        default=Membership.Role.OPERATOR,
    )
    token_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.PENDING,
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="accepted_invitations",
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"], name="org_invite_org_status_idx"),
            models.Index(fields=["email"], name="org_invite_email_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.email} -> {self.organization.slug} ({self.status})"


class OrganizationAPIKey(models.Model):
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_organization_api_keys",
    )
    name = models.CharField(max_length=128)
    key_prefix = models.CharField(max_length=16, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    rate_limit_per_minute = models.PositiveIntegerField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)
    last_used_user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["organization__name", "name"]
        indexes = [
            models.Index(
                fields=["organization", "is_active"],
                name="org_api_key_active_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="org_api_key_expires_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.organization.name}:{self.name}"
