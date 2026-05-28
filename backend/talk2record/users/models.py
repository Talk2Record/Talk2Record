from typing import ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import SET_NULL
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateTimeField
from django.db.models import EmailField
from django.db.models import ForeignKey
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Default custom user model for Talk2Record.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    email = EmailField(_("email address"), unique=True)
    username = None  # type: ignore[assignment]
    onboarding_completed = BooleanField(default=False)
    current_organization = ForeignKey(
        "organizations.Organization",
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="active_users",
    )
    latest_required_legal_acceptance_at = DateTimeField(null=True, blank=True)
    timezone = CharField(max_length=64, default="UTC", blank=True)
    locale = CharField(max_length=16, default="en", blank=True)
    avatar_url = CharField(max_length=512, blank=True, default="")
    mfa_enabled = BooleanField(default=False)
    suspended_at = DateTimeField(null=True, blank=True)
    suspended_reason = CharField(max_length=255, blank=True, default="")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects: ClassVar[UserManager] = UserManager()

    def get_absolute_url(self) -> str:
        """Get URL for a user's admin detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("admin:users_user_change", args=[self.id])


class UserSession(models.Model):
    """Persisted record of an issued refresh token.

    This lets users list + revoke active sessions from the dashboard. The JTI
    comes from the SimpleJWT refresh token and matches what the token-blacklist
    app stores, so revoking here can also blacklist the refresh token.
    """

    user = ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    refresh_jti = CharField(max_length=128, unique=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = CharField(max_length=512, blank=True, default="")
    created_at = DateTimeField(auto_now_add=True)
    last_seen_at = DateTimeField(null=True, blank=True)
    revoked_at = DateTimeField(null=True, blank=True)
    expires_at = DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "revoked_at"],
                name="user_session_user_rev_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.created_at:%Y-%m-%d %H:%M}"
