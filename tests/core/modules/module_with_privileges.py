from quart_babel import lazy_gettext

from superdesk.core.module import Module
from superdesk.core.privileges import Privilege

module = Module(
    name="tests.module_with_privileges",
    privileges=[
        Privilege(name="can_test", description=lazy_gettext("Test privilege can test")),
        Privilege(name="can_play", description=lazy_gettext("Test privilege can play")),
    ],
)
