from os import environ
from subprocess import Popen
from time import sleep
import asyncio

from kombu.utils.objects import cached_property
from celery import Celery, shared_task

from superdesk import get_resource_service
from superdesk.default_settings import strtobool
from superdesk.factory.app import get_app
from superdesk.tests import setup_config


def create_celery_app() -> Celery:
    use_async_worker = strtobool(environ.get("CELERY_USE_ASYNC_WORKER", "true"))
    config = setup_config(
        {
            "CELERY_USE_ASYNC_WORKER": use_async_worker,
            "CELERY_TASK_ALWAYS_EAGER": not use_async_worker,
        }
    )

    sd_app = get_app(config)
    return sd_app.celery


@shared_task()
async def async_task_test(data: dict) -> None:
    service = get_resource_service("system_messages")
    await service.create_async([data])


@shared_task()
def sync_task_test(data: dict) -> None:
    service = get_resource_service("system_messages")
    service.create([data])


@shared_task(store_async_result=True)
async def value_task_test(n: int) -> int:
    return n * 2


@shared_task(soft_time_limit=0.5, time_limit=2)
async def async_task_timeout_test(task_duration: int, cleanup_duration: int) -> None:
    service = get_resource_service("system_messages")

    try:
        await asyncio.sleep(task_duration)
        await service.create_async(
            [{"is_active": True, "type": "success", "message_title": "Test completed", "message": "done"}]
        )
    except asyncio.CancelledError as e:
        await asyncio.sleep(cleanup_duration)
        await service.create_async(
            [
                {
                    "is_active": True,
                    "type": "alert",
                    "message_title": "asyncio.CancelledError",
                    "message": "asyncio.CancelledError",
                }
            ]
        )
        raise


class LazyAppProxy:
    @cached_property
    def _real_app(self):
        return create_celery_app()

    # Route all normal attribute looks down to the real app
    def __getattr__(self, name):
        return getattr(self._real_app, name)


celery_app = LazyAppProxy()


def run_celery_in_background(use_async_worker: bool = True) -> Popen:
    cmd = [
        "celery",
        "-A",
        f"{__name__}:celery_app",
        "worker",
        "--loglevel=INFO",
        "--concurrency=1",
    ]
    env = environ.copy()
    if use_async_worker:
        env["CELERY_USE_ASYNC_WORKER"] = "True"
    process = Popen(cmd, env=env)
    print(f"Celery started successfully with PID: {process.pid}")

    def is_celery_ready():
        try:
            pong = create_celery_app().control.inspect().ping()
            return pong is not None
        except Exception:
            return False

    for _ in range(300):
        if is_celery_ready():
            print("Celery is now ready!")
            break
        sleep(0.1)
    else:
        process.terminate()
        process.wait(timeout=5)
        raise RuntimeError("Timed out waiting for Celery worker to become ready")

    return process
