from quart_babel import lazy_gettext

from superdesk.core.module import Module
from superdesk.core.resources import ResourceConfig, RestEndpointConfig
from superdesk.core.auth.privilege_rules import required_privilege_rule
from superdesk.core.privileges import Privilege
from superdesk.types import AuthServerClientResource


auth_server_client_resource_config = ResourceConfig(
    name="auth_server_clients",
    data_class=AuthServerClientResource,
    rest_endpoints=RestEndpointConfig(
        auth=[required_privilege_rule("auth_server_clients")],
        exclude_fields_in_response={"GET": ["password"]},
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
