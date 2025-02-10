import os
import logging
from celery.signals import worker_process_init

logger = logging.getLogger(__name__)


@worker_process_init.connect
def init_worker_process(sender=None, **kwargs):
    """Initialize each worker process with its own app context.
    This ensures each worker process has its own Flask context.
    """
    from superdesk.factory.app import get_app

    logger.info(f"Initiliazing app for worker subprocess (PID: {os.getpid()})")
    get_app()
