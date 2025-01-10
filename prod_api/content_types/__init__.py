import superdesk
from .service import ContentTypesService
from .resource import ContentTypesResource


def init_app(app) -> None:
    """Initialize the `content_api` API endpoint.

    :param app: the API application object
    :type app: `Eve`
    """
    service = ContentTypesService(datasource="content_types", backend=superdesk.get_backend())
    ContentTypesResource(endpoint_name="content_types", app=app, service=service)
