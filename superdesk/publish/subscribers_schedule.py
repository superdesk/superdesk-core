import logging

from superdesk import get_resource_service
from superdesk.celery_app import celery
from superdesk.dates import get_local_today

logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=30)
def update_subscriber_activation_states():
    """Task to activate/deactivate subscribers whose startDate or endDate matches current today"""
    today = get_local_today().date().isoformat()
    service = get_resource_service("subscribers")

    try:
        # Query for subscribers that have a schedule defined for current date
        lookup = {
            "$or": [
                {"schedule.startDate": today},
                {"schedule.endDate": today},
            ]
        }
        subscribers = list(service.get(req=None, lookup=lookup))
        logger.info(
            "[Subscribers Schedule]: Processing %d subscribers for schedule activation/deactivation", len(subscribers)
        )

        for subscriber in subscribers:
            schedule = subscriber.get("schedule") or {}
            start = schedule.get("startDate")
            end = schedule.get("endDate")
            active = subscriber.get("is_active", False)

            if start == today and not active:
                service.system_update(subscriber["_id"], {"is_active": True}, subscriber)
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' activated (startDate: {start})"
                )
            elif end == today and active:
                service.system_update(subscriber["_id"], {"is_active": False}, subscriber)
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' deactivated (endDate: {end})"
                )

    except Exception:
        logger.exception("[Subscribers Schedule]: Failed to update subscriber activation states based on schedule.")
