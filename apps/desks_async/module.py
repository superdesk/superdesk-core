from superdesk.core.resources import ResourceConfig, MongoResourceConfig, MongoIndexOptions
from superdesk.types import DesksResourceModel
from .desks_async_service import DesksAsyncService

desks_resource_config = ResourceConfig(
    name="desks",
    data_class=DesksResourceModel,
    service=DesksAsyncService,
    default_sort=[("name", 1)],
    mongo=MongoResourceConfig(
        indexes=[
            MongoIndexOptions(
                name="name_1",
                keys=[("name", 1)],
                unique=True,
            ),
        ],
    ),
)
