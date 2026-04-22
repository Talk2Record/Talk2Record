"""Reusable DRF permissions for organization-scoped resources.

These enforce the role hierarchy defined on ``Membership``:

- ``owner`` > ``admin`` > ``operator``

Every permission assumes the request is already ``IsAuthenticated``. They
resolve the active organization via ``OrganizationContextService`` (which
honours ``User.current_organization`` and falls back to the first membership).
"""

from __future__ import annotations

from rest_framework.permissions import BasePermission

from talk2record.organizations.models import Membership
from talk2record.organizations.services import OrganizationContextService


def _resolve_role(request) -> tuple[str | None, object | None]:
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return None, None
    context = OrganizationContextService.resolve_user_context(user)
    if context is None:
        return None, None
    return context.role, context.organization


class IsOrgMember(BasePermission):
    """User must belong to at least one organization."""

    message = "Organization membership required."

    def has_permission(self, request, view) -> bool:
        role, _organization = _resolve_role(request)
        return role is not None


class IsOrgAdmin(BasePermission):
    """User must be ``owner`` or ``admin`` of their active organization."""

    message = "Organization admin role required."
    _allowed = {Membership.Role.OWNER, Membership.Role.ADMIN}

    def has_permission(self, request, view) -> bool:
        role, _organization = _resolve_role(request)
        return role in self._allowed


class IsOrgOwner(BasePermission):
    """User must be ``owner`` of their active organization."""

    message = "Organization owner role required."

    def has_permission(self, request, view) -> bool:
        role, _organization = _resolve_role(request)
        return role == Membership.Role.OWNER


class IsPlatformStaff(BasePermission):
    """Platform-admin surface: ``is_staff`` OR ``is_superuser``."""

    message = "Platform staff role required."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        return bool(user.is_staff or user.is_superuser)
