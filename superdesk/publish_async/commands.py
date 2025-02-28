from superdesk.commands import cli
from superdesk.celery_app import celery
from .controller.exchanges import get_exchange_factory


@cli.command("publish:transmit")
async def publish_pending_items():
    """
    Command to transmit and publish all pending items.

    This asynchronous function fetches the exchange factory and initiates
    the processing of pending tasks. Useful for ensuring any delayed or
    queued items are published as required.

    Returns:
        None
    """

    await get_exchange_factory().process_pending_tasks()


@celery.task(soft_time_limit=1800, expires=10)
async def transmit():
    """
    Asynchronous task for processing pending exchange tasks with specific
    time constraints using Celery. This task is set up to have a soft time
    limit and an expiration time, ensuring efficient task execution and
    preventing runaway processes.

    Args:
        None

    Returns:
        None
    """

    await get_exchange_factory().process_pending_tasks()
