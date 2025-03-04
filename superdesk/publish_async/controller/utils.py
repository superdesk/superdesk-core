from superdesk.core import get_config


def get_publish_celery_queue(context: str | None = None) -> str:
    if context is None:
        context = "DEFAULT"

    return get_config(str, f"PUBLISH_{context.upper()}_CELERY_QUEUE", "PUBLISH_DEFAULT_CELERY_QUEUE")


def get_high_priority_celery_queue(priority: bool | None = None) -> str:
    return (
        get_config(str, "HIGH_PRIORITY_QUEUE")
        if priority and get_config(bool, "HIGH_PRIORITY_QUEUE_ENABLED")
        else get_publish_celery_queue()
    )
