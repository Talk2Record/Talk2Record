from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.users.models import UserSession


@pytest.mark.django_db
class TestSessionEndpoints:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_login_creates_session_and_list_shows_it(self, api_client, workspace_user):
        workspace_user.set_password("secret-pass-123")
        workspace_user.save(update_fields=["password"])
        login_response = api_client.post(
            reverse("api-auth-login"),
            data={"email": workspace_user.email, "password": "secret-pass-123"},
            format="json",
        )
        assert login_response.status_code == status.HTTP_200_OK
        assert "refresh" in login_response.data
        sessions = UserSession.objects.filter(user=workspace_user)
        assert sessions.count() == 1

        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )
        list_response = api_client.get(reverse("api-auth-sessions"))
        assert list_response.status_code == status.HTTP_200_OK
        assert len(list_response.data) == 1

    def test_revoke_session(self, api_client, workspace_user):
        workspace_user.set_password("secret-pass-123")
        workspace_user.save(update_fields=["password"])
        login_response = api_client.post(
            reverse("api-auth-login"),
            data={"email": workspace_user.email, "password": "secret-pass-123"},
            format="json",
        )
        session = UserSession.objects.get(user=workspace_user)
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )
        revoke_response = api_client.delete(
            reverse("api-auth-sessions-revoke", kwargs={"session_id": session.pk}),
        )
        assert revoke_response.status_code == status.HTTP_204_NO_CONTENT
        session.refresh_from_db()
        assert session.revoked_at is not None

    def test_logout_marks_session_revoked(self, api_client, workspace_user):
        workspace_user.set_password("secret-pass-123")
        workspace_user.save(update_fields=["password"])
        login_response = api_client.post(
            reverse("api-auth-login"),
            data={"email": workspace_user.email, "password": "secret-pass-123"},
            format="json",
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )
        logout_response = api_client.post(
            reverse("api-auth-logout"),
            data={"refresh": login_response.data["refresh"]},
            format="json",
        )
        assert logout_response.status_code == status.HTTP_204_NO_CONTENT
        session = UserSession.objects.get(user=workspace_user)
        assert session.revoked_at is not None
