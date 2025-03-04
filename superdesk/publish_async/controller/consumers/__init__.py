from .asyncio_consumer import AsyncioPublishConsumer
from .celery_consumer import CeleryPublishConsumer

consumers = [AsyncioPublishConsumer, CeleryPublishConsumer]
