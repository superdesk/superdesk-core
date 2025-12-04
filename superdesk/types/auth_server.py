from typing import Annotated
from enum import Enum, unique
import bcrypt

from bson import ObjectId
from pydantic import Field, StringConstraints, field_validator

from superdesk.core.resources import ResourceModelWithObjectId
from superdesk.core.resources.validators import validate_iunique_value_async

from superdesk.utils import gen_password

# please refer to /docs/auth_server.rst for details on scopes

"""Scopes allowed in auth_server"""


@unique
class AuthServerScope(str, Enum):
    ARCHIVE_READ = "ARCHIVE_READ"
    DESKS_READ = "DESKS_READ"
    PLANNING_READ = "PLANNING_READ"
    CONTACTS_READ = "CONTACTS_READ"
    USERS_READ = "USERS_READ"
    ASSIGNMENTS_READ = "ASSIGNMENTS_READ"
    EVENTS_READ = "EVENTS_READ"


allowed_auth_server_scopes = {s.name for s in AuthServerScope}


class AuthServerClientResource(ResourceModelWithObjectId):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
        validate_iunique_value_async("auth_server_clients", "name"),
    ]
    password: Annotated[
        str,
        Field(default_factory=gen_password),
    ]
    scope: Annotated[list[AuthServerScope], Field(min_length=1)]

    @field_validator("id", mode="before")
    def parse_id(cls, value: str | ObjectId | None) -> ObjectId:
        if isinstance(value, ObjectId):
            return value

        return ObjectId(value) if value and value.strip() else ObjectId()

    @field_validator("password", mode="before")
    def parse_password(cls, value: str | None) -> str:
        password = gen_password() if not value or not value.strip() else value
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @field_validator("scope", mode="after")
    def parse_scope(cls, scopes: list[AuthServerScope]) -> list[AuthServerScope]:
        # Make sure to return unique only
        return list(set(scopes))
