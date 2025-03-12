from pprint import pprint
from superdesk.core import get_config

from superdesk.types import PublishRequest, PublishRequestResponse, ContentType
from superdesk.commands import cli
from superdesk.celery_app import celery
from superdesk.default_settings import PublishChannelConfig
from superdesk.profiling import ProfileManager

from . import get_exchange_factory


@cli.command("publish:transmit")
async def publish_pending_items():
    """
    Command to transmit and publish all pending items.

    This asynchronous function fetches the exchange factory and initiates
    the processing of pending tasks. Useful for ensuring any delayed or
    queued items are published as required.
    """

    await get_exchange_factory().process_pending_tasks()


@cli.command("publish:enqueue")
async def publish_scheduled_items():
    """
    Command to transmit and publish all scheduled items (if the schedule has elapsed).

    This asynchronous function fetches the exchange factory and initiates
    the processing of pending tasks. Useful for ensuring any delayed or
    queued items are published as required.
    """
    await get_exchange_factory().send_scheduled_or_pending_content()


@cli.command("publish:print_types")
def print_publish_component_types():
    factory = get_exchange_factory()
    channels = get_config(list[PublishChannelConfig], "PUBLISH_CHANNELS")

    item_types = [
        ContentType.TEXT,
        ContentType.PREFORMATTED,
        ContentType.AUDIO,
        ContentType.VIDEO,
        ContentType.PICTURE,
        ContentType.GRAPHIC,
        ContentType.COMPOSITE,
        ContentType.EVENT,
        ContentType.PLANNING,
        ContentType.FEATURED_PLANNING,
    ]
    operations = [
        "publish",
        "correct",
        "kill",
        "takedown",
        "unpublish",
        "being_corrected",
        "resend",
    ]

    print("Channel Configs:")
    pprint(channels)

    print("\nFilter Classes:")
    pprint(factory._filter_classes)

    print("\nFormatter Classes:")
    pprint(factory._formatter_classes)

    print("\nRouter Classes:")
    pprint(factory._router_classes)

    print("\nExchange Classes:")
    pprint(factory._exchange_classes)

    print("\nSupported Publish Channels:")
    for item_type in item_types:
        print(f"{item_type}:")
        for operation in operations:
            exchange = factory.get_exchange(
                PublishRequest(
                    item={},
                    item_id="",
                    operation=operation,
                    published_state="published",
                    item_type=item_type,
                    sender_type="api",
                )
            )
            print(
                f"    {operation}: Exchange(exchange={exchange.name}, filter={exchange._filter.name}, formatter={exchange._formatter.name}, router={exchange._router.name})"
            )


@celery.task(soft_time_limit=1800, expires=10)
async def transmit():
    """
    Asynchronous task for processing pending exchange tasks with specific
    time constraints using Celery. This task is set up to have a soft time
    limit and an expiration time, ensuring efficient task execution and
    preventing runaway processes.
    """

    await get_exchange_factory().process_pending_tasks()


async def publish_item(request: PublishRequest) -> PublishRequestResponse:
    return await get_exchange_factory().send(request)


@celery.task(soft_time_limit=600)
async def enqueue_published():
    """Pick new items from ``published`` collection and enqueue it."""
    with ProfileManager("publish:enqueue"):
        await get_exchange_factory().send_scheduled_or_pending_content()
