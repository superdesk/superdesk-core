from bson import ObjectId
from superdesk.types import UsersResourceModel


ADMIN_USER_ID = ObjectId()


def admin() -> UsersResourceModel:
    return UsersResourceModel(
        id=ADMIN_USER_ID,
        username="admin",
        password="admin",
        email="foo@bar.org",
        first_name="foo",
        last_name="bar",
        display_name="foo bar",
        is_active=True,
        is_enabled=True,
        needs_activation=False,
        sign_off="abc",
    )


def all_users() -> list[UsersResourceModel]:
    return [admin()]
