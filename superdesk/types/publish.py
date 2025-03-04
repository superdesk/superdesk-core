from typing import Protocol

from .subscribers import SubscribersResource
from .publish_queue import PublishQueueResource


class PublishConsumer(Protocol):
    """
    Defines the protocol for a publish-consumer that facilitates handling and processing
    tasks and transmitting items between publishers and subscribers.

    This protocol is intended to formalize the behavior of implementing classes that manage
    communication and task dispatch between a publisher's task queue and subscriber resources.

    Methods:
        process_tasks: Represents the mechanism to process and handle multiple tasks
                       for a given subscriber resource.
        transmit_item: Represents the mechanism to transmit a single task item
                       from the publish queue.

    """

    async def process_tasks(self, subscriber: SubscribersResource, tasks: list[PublishQueueResource]) -> None:
        ...

    async def transmit_item(self, task: PublishQueueResource) -> bool:
        ...
