from superdesk.core.types import MongoResourceConfig
from superdesk.core.app import SuperdeskAsyncApp

from ..resources import ResourceConfig


def on_resource_registered(app: SuperdeskAsyncApp, config: ResourceConfig) -> None:
    mongo_config = config.mongo or MongoResourceConfig()
    if config.versioning:
        mongo_config.versioning = True

    app.mongo.register_resource_config(config.name, mongo_config)
