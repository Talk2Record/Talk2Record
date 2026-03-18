import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from talk2record.users.models import User
from talk2record.users.tests.factories import UserFactory
from talk2record.users.views import UserViewSet


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        assert response.data == {
            "id": user.pk,
            "email": user.email,
            "url": f"http://testserver/api/users/{user.pk}/",
            "name": user.name,
        }


@pytest.mark.django_db
class TestJWTAuthAPI:
    @pytest.fixture
    def api_client(self) -> APIClient:
        return APIClient()

    def test_login_returns_tokens_and_user(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)

        response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data) == {"refresh", "access", "user"}
        assert response.data["user"] == {
            "id": user.pk,
            "email": user.email,
            "url": f"http://testserver/api/users/{user.pk}/",
            "name": user.name,
        }

    def test_current_user_requires_jwt(self, api_client: APIClient):
        response = api_client.get(reverse("api-auth-me"))

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_current_user_returns_authenticated_user(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        response = api_client.get(reverse("api-auth-me"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            "id": user.pk,
            "email": user.email,
            "url": f"http://testserver/api/users/{user.pk}/",
            "name": user.name,
        }

    def test_verify_accepts_valid_access_token(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )

        response = api_client.post(
            reverse("api-auth-verify"),
            {"token": login_response.data["access"]},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK

    def test_logout_blacklists_refresh_token(self, api_client: APIClient):
        password = "T3stPassword!123"
        user = UserFactory.create(password=password)
        login_response = api_client.post(
            reverse("api-auth-login"),
            {"email": user.email, "password": password},
            format="json",
        )
        api_client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}",
        )

        logout_response = api_client.post(
            reverse("api-auth-logout"),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )
        refresh_response = api_client.post(
            reverse("api-auth-refresh"),
            {"refresh": login_response.data["refresh"]},
            format="json",
        )

        assert logout_response.status_code == status.HTTP_204_NO_CONTENT
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
