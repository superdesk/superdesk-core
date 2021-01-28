from flask_babel import lazy_gettext
import superdesk
from .content_types import ContentTypesResource, ContentTypesService, CONTENT_TYPE_PRIVILEGE
from .content_types import apply_schema  # noqa


def init_app(app) -> None:
    endpoint_name = "content_types"
    service = ContentTypesService(endpoint_name, backend=superdesk.get_backend())
    ContentTypesResource(endpoint_name, app=app, service=service)
    superdesk.privilege(name=CONTENT_TYPE_PRIVILEGE, label=lazy_gettext("Content Profile"), description=lazy_gettext("Manage content profiles"))
