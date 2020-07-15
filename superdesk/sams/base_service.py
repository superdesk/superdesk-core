from dateutil.parser import parse
from sams_client import SamsClient
from superdesk.services import Service


class BaseService(Service):
    """
    Base service for sams endpoints, defines the SamsClient instance and
    helper methods
    """
    def __init__(self, configs=None, **kwargs):
        super(BaseService, self).__init__(**kwargs)
        self.client = SamsClient(configs)

    def parse_date(self, arg):
        """
        Parses _created and _updated string fields
        """
        arg['_created'] = parse(arg['_created'])
        arg['_updated'] = parse(arg['_updated'])
        return arg
