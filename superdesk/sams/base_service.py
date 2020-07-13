from superdesk.services import Service
from sams_client import SamsClient


class BaseService(Service):

    def __init__(self, configs=None, **kwargs):
        super(BaseService, self).__init__(**kwargs)
        self.client = SamsClient(configs)

    def to_dict(self, arg: dict):
        remove_fields = ['_created', '_updated', '_etag', '_links']
        return dict(
            (key, arg[key]) for key in set(arg.keys()) - set(remove_fields)
        )
