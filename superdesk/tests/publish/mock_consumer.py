from superdesk.types import PublishQueueResource, PublishQueueState
from superdesk.publish_async.consumers import AsyncioPublishConsumer


class MockPublishConsumer(AsyncioPublishConsumer):
    name: str = "mock"

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        if task.destination and task.destination.delivery_type == "File":
            # If the destination is a local file, then follow normal consumer code
            return await super().transmit_item(task)

        # Otherwise mock transmission and simply mark the item as published
        await PublishQueueResource.get_service().update(task.id, {"state": PublishQueueState.SUCCESS}, task.etag, task)
        return True


publish_components = [MockPublishConsumer]
