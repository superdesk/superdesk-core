import superdesk

from .resource import AvailabilityResource
from .service import AvailabilityService


def init_app(app):
    endpoint_name = "user_availability"
    service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())
    AvailabilityResource(endpoint_name, app=app, service=service)
