from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService


class DefaultUserAvailabilityResource(Resource):
    internal_resource = True


class DefaultUserAvailabilityService(AsyncBaseService):
    pass
