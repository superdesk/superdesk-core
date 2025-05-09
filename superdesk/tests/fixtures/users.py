from bson import ObjectId
from superdesk.types import UsersResourceModel, UserTypeEnum


ADMIN_USER_ID = ObjectId()
FOOBAR_USER_ID = ObjectId()


def admin() -> UsersResourceModel:
    return UsersResourceModel(
        id=ADMIN_USER_ID,
        username="admin",
        password="admin",
        email="foo@bar.org",
        first_name="foo",
        last_name="bar",
        display_name="Foo Bar",
        is_active=True,
        is_enabled=True,
        needs_activation=False,
        sign_off="abc",
        user_type=UserTypeEnum.ADMINISTRATOR,
    )


def foobar() -> UsersResourceModel:
    return UsersResourceModel(
        id=FOOBAR_USER_ID,
        username="foobar",
        password="admin",
        email="foo.rickidy@bar.org",
        first_name="foo",
        last_name="bar",
        display_name="Foo Rickidy Bar",
        is_active=True,
        is_enabled=True,
        needs_activation=False,
        sign_off="frb",
    )


def all_users() -> list[UsersResourceModel]:
    return [admin(), foobar()]
