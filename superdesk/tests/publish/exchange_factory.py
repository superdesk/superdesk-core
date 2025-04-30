from superdesk.types import SubscribersResource, PublishConsumer
from superdesk.publish_async.exchanges import DefaultPublishExchangeFactory
from superdesk.publish_async.consumers import ContentApiPublishConsumer


class MockPublishExchangeFactory(DefaultPublishExchangeFactory):
    def get_subscriber_consumer(self, subscriber: SubscribersResource) -> PublishConsumer:
        consumer = super().get_subscriber_consumer(subscriber)
        return consumer if consumer.name == ContentApiPublishConsumer.name else self.get_consumer("mock")
