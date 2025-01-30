from quart_babel import lazy_gettext

from superdesk.core.module import Module
from superdesk.core.privileges import Privilege
from superdesk.core.auth.privilege_rules import http_method_privilege_based_rules
from superdesk.core.resources import ResourceConfig, ResourceModel, RestEndpointConfig

test_privileges = ["can_read", "can_create"]

resource_config = ResourceConfig(
    name="privileged_resource",
    data_class=ResourceModel,
    rest_endpoints=RestEndpointConfig(
        resource_methods=["GET", "POST"],
        auth=http_method_privilege_based_rules({"GET": test_privileges[0], "POST": test_privileges[1]}),
    ),
)


module = Module(
    name="tests.module_with_privileges",
    resources=[resource_config],
    privileges=[
        Privilege(name="can_read", description=lazy_gettext("Test privilege can read")),
        Privilege(name="can_create", description=lazy_gettext("Test privilege can create")),
    ],
)
