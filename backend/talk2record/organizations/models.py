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
