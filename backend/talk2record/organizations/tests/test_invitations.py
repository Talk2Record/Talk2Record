from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.organizations.invitations import InvitationError
from talk2record.organizations.invitations import MembershipInvitationService
from talk2record.organizations.models import Membership
from talk2record.organizations.models import MembershipInvitation
from talk2record.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestInvitationService:
    def test_create_and_accept_invitation(self, organization, workspace_user):
        invitee = UserFactory.create(email="invitee@example.com")
        created = MembershipInvitationService.create(
            organization=organization,
            email="invitee@example.com",
            role=Membership.Role.OPERATOR,
            invited_by=workspace_user,
        )
        assert created.raw_token.split(".", 1)[0].isdigit()
        assert created.invitation.status == MembershipInvitation.Status.PENDING

        membership = MembershipInvitationService.accept(
            raw_token=created.raw_token,
            user=invitee,
        )
        assert membership.organization == organization
        assert membership.role == Membership.Role.OPERATOR
        created.invitation.refresh_from_db()
        assert created.invitation.status == MembershipInvitation.Status.ACCEPTED
        assert created.invitation.accepted_by == invitee

    def test_cannot_accept_with_different_email(self, organization, workspace_user):
        other = UserFactory.create(email="other@example.com")
        created = MembershipInvitationService.create(
            organization=organization,
            email="target@example.com",
            role=Membership.Role.OPERATOR,
            invited_by=workspace_user,
        )
        with pytest.raises(InvitationError):
            MembershipInvitationService.accept(raw_token=created.raw_token, user=other)

    def test_cannot_invite_existing_member(self, organization, workspace_user):
        with pytest.raises(InvitationError):
            MembershipInvitationService.create(
                organization=organization,
                email=workspace_user.email,
                role=Membership.Role.ADMIN,
                invited_by=workspace_user,
            )

    def test_cannot_remove_last_owner(self, organization, workspace_user):
        membership = workspace_user.memberships.get()
        with pytest.raises(InvitationError):
            MembershipInvitationService.remove(membership=membership, actor=workspace_user)

    def test_change_role(self, organization, workspace_user):
        invitee = UserFactory.create(email="change-role@example.com")
        Membership.objects.create(
            user=invitee,
            organization=organization,
            role=Membership.Role.OPERATOR,
        )
        membership = invitee.memberships.get()
        MembershipInvitationService.change_role(
            membership=membership,
            new_role=Membership.Role.ADMIN,
            actor=workspace_user,
        )
        membership.refresh_from_db()
        assert membership.role == Membership.Role.ADMIN


@pytest.mark.django_db
class TestInvitationAPI:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_admin_can_invite_and_list(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        url = reverse("api:membership-invitations")
        response = api_client.post(
            url,
            data={"email": "new@example.com", "role": Membership.Role.OPERATOR},
            format="json",
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["token"].split(".", 1)[0].isdigit()
        assert response.data["invitation"]["email"] == "new@example.com"

        list_response = api_client.get(url)
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data) == 1

    def test_operator_cannot_invite(self, api_client, organization):
        operator_user = UserFactory.create(email="operator@example.com")
        Membership.objects.create(
            user=operator_user,
            organization=organization,
            role=Membership.Role.OPERATOR,
        )
        operator_user.current_organization = organization
        operator_user.save(update_fields=["current_organization"])
        api_client.force_authenticate(user=operator_user)
        response = api_client.post(
            reverse("api:membership-invitations"),
            data={"email": "x@example.com", "role": Membership.Role.OPERATOR},
            format="json",
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_accept_invitation_endpoint(self, api_client, workspace_user, organization):
        invitee = UserFactory.create(email="joiner@example.com")
        created = MembershipInvitationService.create(
            organization=organization,
            email="joiner@example.com",
            role=Membership.Role.OPERATOR,
            invited_by=workspace_user,
        )
        api_client.force_authenticate(user=invitee)
        response = api_client.post(
            reverse("api-invitation-accept"),
            data={"token": created.raw_token},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert Membership.objects.filter(user=invitee, organization=organization).exists()

    def test_invitation_lookup_unauthenticated(self, api_client, workspace_user, organization):
        created = MembershipInvitationService.create(
            organization=organization,
            email="look@example.com",
            role=Membership.Role.OPERATOR,
            invited_by=workspace_user,
        )
        response = api_client.get(
            reverse("api-invitation-lookup", kwargs={"token": created.raw_token}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == "look@example.com"

    def test_revoke_invitation(self, api_client, workspace_user, organization):
        created = MembershipInvitationService.create(
            organization=organization,
            email="r@example.com",
            role=Membership.Role.OPERATOR,
            invited_by=workspace_user,
        )
        api_client.force_authenticate(user=workspace_user)
        response = api_client.post(
            reverse(
                "api:membership-revoke-invitation",
                kwargs={"invitation_id": created.invitation.pk},
            ),
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        created.invitation.refresh_from_db()
        assert created.invitation.status == MembershipInvitation.Status.REVOKED

    def test_change_membership_role_endpoint(
        self,
        api_client,
        workspace_user,
        organization,
    ):
        member = UserFactory.create(email="member@example.com")
        membership = Membership.objects.create(
            user=member,
            organization=organization,
            role=Membership.Role.OPERATOR,
        )
        api_client.force_authenticate(user=workspace_user)
        response = api_client.patch(
            reverse("api:membership-change-role", kwargs={"pk": membership.pk}),
            data={"role": Membership.Role.ADMIN},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        membership.refresh_from_db()
        assert membership.role == Membership.Role.ADMIN

    def test_mine_endpoint_returns_memberships(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(reverse("api:membership-mine"))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
