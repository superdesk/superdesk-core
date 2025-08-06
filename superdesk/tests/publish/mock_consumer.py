from superdesk.types import PublishQueueResource, PublishQueueState
from superdesk.publish_async.consumers import AsyncioPublishConsumer


class MockPublishConsumer(AsyncioPublishConsumer):
    name: str = "mock"

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        if self._allow_normal_publish(task):
            # If the destination is a local file, then follow normal consumer code
            return await super().transmit_item(task)

        # Otherwise mock transmission and simply mark the item as published
        await PublishQueueResource.get_service().update(task.id, {"state": PublishQueueState.SUCCESS}, task.etag, task)
        return True

    def _allow_normal_publish(self, task: PublishQueueResource) -> bool:
        if not task.destination:
            return False

        delivery_type = "" if not task.destination else task.destination.delivery_type.lower()

        if delivery_type == "file":
            # Allow local file transmission
            return True
        elif delivery_type == "http_push":
            # Allow mock HTTP transmission
            config = {} if not task.destination.config else task.destination.config.copy()
            return config.get("resource_url") == "mock://publish" and config.get("assets_url") == "mock://assets"

        return False


publish_components = [MockPublishConsumer]
