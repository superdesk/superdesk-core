from superdesk.types import PublishQueueResource, PublishQueueState
from superdesk.publish_async.consumers import AsyncioPublishConsumer


class MockPublishConsumer(AsyncioPublishConsumer):
    name: str = "mock"

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        await PublishQueueResource.get_service().update(task.id, {"state": PublishQueueState.SUCCESS}, task.etag, task)
        return True


publish_components = [MockPublishConsumer]
