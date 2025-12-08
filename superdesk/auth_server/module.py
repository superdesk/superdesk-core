import bcrypt

from quart_babel import lazy_gettext
from bson import ObjectId

from superdesk.core.module import Module
from superdesk.core.resources import ResourceConfig, RestEndpointConfig, AsyncResourceService
from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.privileges import Privilege
from superdesk.types import AuthServerClientResource


class AuthServerClientService(AsyncResourceService[AuthServerClientResource]):
    async def insert_into_dbs(self, doc: AuthServerClientResource) -> tuple[str | ObjectId, str]:
        # We want to return to the client the provided/generated password
        # and not the hashed version stored in the DB

        provided_password = doc.password
        doc.password = bcrypt.hashpw(doc.password.encode(), bcrypt.gensalt()).decode()
        doc_id, doc_etag = await super().insert_into_dbs(doc)
        doc.password = provided_password
        return doc_id, doc_etag

    async def update_in_dbs(
        self,
        item_id: str | ObjectId,
        original: AuthServerClientResource,
        updates: dict,
        validated_updates: dict,
    ) -> dict:
        # We want to return to the client the provided/generated password
        # and not the hashed version stored in the DB

        if "password" not in updates:
            return await super().update_in_dbs(item_id, original, updates, validated_updates)

        unhashed_password = updates["password"]
        updates["password"] = bcrypt.hashpw(unhashed_password.encode(), bcrypt.gensalt()).decode()
        updates_dict = await super().update_in_dbs(item_id, original, updates, validated_updates)
        updates_dict["password"] = unhashed_password

        return updates_dict


auth_server_client_resource_config = ResourceConfig(
    name="auth_server_clients",
    data_class=AuthServerClientResource,
    service=AuthServerClientService,
    rest_endpoints=RestEndpointConfig(
        auth=[required_privilege_rule("auth_server_clients")],
        exclude_fields_in_response={"GET": ["password"], "PATCH": ["password"]},
    ),
)

module = Module(
    name="superdesk.auth_server",
    resources=[auth_server_client_resource_config],
    privileges=[
        Privilege(
            name="auth_server_clients",
            label=lazy_gettext("Auth Server Clients"),
            description=lazy_gettext("User can manage auth server clients"),
        ),
    ],
)
