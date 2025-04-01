import superdesk

from .availability import AvailabilityResource, AvailabilityService
from .default_availability import DefaultAvailabilityResource, DefaultAvailabilityService


def init_app(app):
    endpoint_name = "user_availability"
    service = AvailabilityService(endpoint_name, backend=superdesk.get_backend())
    AvailabilityResource(endpoint_name, app=app, service=service)

    default_endpoint_name = "default_user_availability"
    default_service = DefaultAvailabilityService(default_endpoint_name, backend=superdesk.get_backend())
    DefaultAvailabilityResource(default_endpoint_name, app=app, service=default_service)
