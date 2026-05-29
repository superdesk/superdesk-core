from os import environ
from subprocess import Popen
from time import sleep

from quart import Config

from superdesk import get_resource_service
from superdesk.factory import get_app
from superdesk.tests import update_config


config = Config({})
config.from_object("superdesk.default_settings")
update_config(config)

sd_app = get_app(config)
celery = sd_app.celery


@celery.task()
async def async_task_test(data: dict) -> None:
    service = get_resource_service("system_messages")
    await service.create_async([data])


@celery.task()
def sync_task_test(data: dict) -> None:
    service = get_resource_service("system_messages")
    service.create([data])


def run_celery_in_background(use_async_worker: bool = True) -> Popen:
    cmd = [
        "celery",
        "-A",
        "superdesk.tests.worker",
        "worker",
        "--loglevel=ERROR",
        "--concurrency=1",
    ]
    env = environ.copy()
    if use_async_worker:
        env["CELERY_USE_ASYNC_WORKER"] = "True"
    process = Popen(cmd, env=env)
    print(f"Celery started successfully with PID: {process.pid}")

    def is_celery_ready():
        try:
            pong = celery.control.inspect().ping()
            return pong is not None
        except Exception:
            return False

    while True:
        if is_celery_ready():
            print("Celery is now ready!")
            break
        sleep(0.1)

    return process
