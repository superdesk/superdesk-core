
from flask_babel import _

from .common import BasePublishResource, ITEM_UNPUBLISH, CONTENT_STATE, PUB_STATUS, ITEM_KILL
from .kill import KillPublishService


class UnpublishResource(BasePublishResource):
    def __init__(self, endpoint_name, app, service):
        super().__init__(endpoint_name, app, service, ITEM_UNPUBLISH)
    pass


class UnpublishService(KillPublishService):
    publish_type = ITEM_KILL
    item_operation = ITEM_UNPUBLISH
    published_state = CONTENT_STATE.UNPUBLISHED
    VALIDATE_ERROR_MESSAGE = _(
        'This item is in a package. It needs to be removed before the item can be unpublished.'
    )

    def __init__(self, datasource=None, backend=None):
        super().__init__(datasource=datasource, backend=backend)

    def apply_kill_override(self, item, updates):
        pass

    def apply_kill_template(self, item):
        pass

    def broadcast_kill_email(self, original, updates):
        pass
