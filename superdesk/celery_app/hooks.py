import logging
from os import getpid

from celery.signals import worker_process_init, worker_shutting_down
from .async_worker import CeleryAsyncWorkerThread

__all__ = ["start_async_thread", "shutdown_async_thread"]


logger = logging.getLogger(__name__)


def start_async_thread(sender, **kwargs):
    logger.info(f"on_worker_init[{getpid()}]")
    # Get the instance here, which will automatically start the thread
    CeleryAsyncWorkerThread.get_instance()


def shutdown_async_thread(sender, **kwargs):
    logger.info(f"on_worker_shutting_down[{getpid()}]")
    try:
        CeleryAsyncWorkerThread.get_instance(raise_if_not_available=True).stop()
    except CeleryAsyncWorkerThread.WorkerNotCreatedException:
        pass


def connect_signals():
    worker_process_init.connect(start_async_thread)
    worker_shutting_down.connect(shutdown_async_thread)
