from superdesk.core.app import SuperdeskAsyncApp

from ..resources import ResourceConfig


def on_resource_registered(app: SuperdeskAsyncApp, config: ResourceConfig) -> None:
    if not config.elastic:
        return
    elif config.default_sort:
        config.elastic.default_sort = config.default_sort

    app.elastic.register_resource_config(
        config.name,
        config.elastic,
    )
