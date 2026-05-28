from __future__ import annotations

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestAdminUserEndpoints:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    @pytest.fixture
    def staff_user(self) -> User:
        user = UserFactory.create(email="staff@example.com")
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["is_staff", "is_superuser"])
        return user

    def test_non_staff_cannot_list_users(self, api_client, workspace_user):
        api_client.force_authenticate(user=workspace_user)
        response = api_client.get(reverse("api:admin-user-list"))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_staff_can_list_users(self, api_client, staff_user):
        UserFactory.create(email="one@example.com")
        UserFactory.create(email="two@example.com")
        api_client.force_authenticate(user=staff_user)
        response = api_client.get(reverse("api:admin-user-list"))
        assert response.status_code == status.HTTP_200_OK
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        assert len(results) >= 3

    def test_staff_can_suspend_and_reactivate_user(self, api_client, staff_user):
        target = UserFactory.create(email="target@example.com")
        api_client.force_authenticate(user=staff_user)

        response = api_client.post(
            reverse("api:admin-user-suspend", kwargs={"pk": target.pk}),
            data={"reason": "abuse"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is False
        assert target.suspended_at is not None

        response = api_client.post(
            reverse("api:admin-user-reactivate", kwargs={"pk": target.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.is_active is True
        assert target.suspended_at is None

    def test_staff_cannot_suspend_themselves(self, api_client, staff_user):
        api_client.force_authenticate(user=staff_user)
        response = api_client.post(
            reverse("api:admin-user-suspend", kwargs={"pk": staff_user.pk}),
            data={},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_staff_can_impersonate(self, api_client, staff_user):
        target = UserFactory.create(email="imp@example.com")
        api_client.force_authenticate(user=staff_user)
        response = api_client.post(
            reverse("api:admin-user-impersonate", kwargs={"pk": target.pk}),
        )
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert response.data["user"]["id"] == target.pk

    def test_search_filters(self, api_client, staff_user):
        UserFactory.create(email="find-me@example.com", name="Findable")
        api_client.force_authenticate(user=staff_user)
        response = api_client.get(
            reverse("api:admin-user-list"),
            {"search": "find-me"},
        )
        assert response.status_code == status.HTTP_200_OK
        results = (
            response.data
            if isinstance(response.data, list)
            else response.data.get("results", [])
        )
        emails = [row["email"] for row in results]
        assert any("find-me@example.com" in e for e in emails)
