from talk2record.users.models import User


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/admin/users/user/{user.pk}/change/"
