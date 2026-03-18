from django.urls import resolve
from django.urls import reverse

from talk2record.users.models import User


def test_user_detail(user: User):
    assert (
        reverse("api:user-detail", kwargs={"pk": user.pk}) == f"/api/users/{user.pk}/"
    )
    assert resolve(f"/api/users/{user.pk}/").view_name == "api:user-detail"


def test_user_list():
    assert reverse("api:user-list") == "/api/users/"
    assert resolve("/api/users/").view_name == "api:user-list"


def test_user_me():
    assert reverse("api:user-me") == "/api/users/me/"
    assert resolve("/api/users/me/").view_name == "api:user-me"


def test_auth_login():
    assert reverse("api-auth-login") == "/api/auth/login/"
    assert resolve("/api/auth/login/").view_name == "api-auth-login"


def test_auth_refresh():
    assert reverse("api-auth-refresh") == "/api/auth/refresh/"
    assert resolve("/api/auth/refresh/").view_name == "api-auth-refresh"


def test_auth_verify():
    assert reverse("api-auth-verify") == "/api/auth/verify/"
    assert resolve("/api/auth/verify/").view_name == "api-auth-verify"


def test_auth_logout():
    assert reverse("api-auth-logout") == "/api/auth/logout/"
    assert resolve("/api/auth/logout/").view_name == "api-auth-logout"


def test_auth_me():
    assert reverse("api-auth-me") == "/api/auth/me/"
    assert resolve("/api/auth/me/").view_name == "api-auth-me"
