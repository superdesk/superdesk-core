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
                {"schedule.start_date": today},
                {"schedule.end_date": today},
            ]
        }
        subscribers = list(service.get(req=None, lookup=lookup))
        logger.info(
            "[Subscribers Schedule]: Processing %d subscribers for schedule activation/deactivation", len(subscribers)
        )

        for subscriber in subscribers:
            schedule = subscriber.get("schedule") or {}
            start = schedule.get("start_date")
            end = schedule.get("end_date")
            active = subscriber.get("is_active", False)

            if start == today and not active:
                service.system_update(subscriber["_id"], {"is_active": True}, subscriber)
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' activated (start_date: {start})"
                )
            elif end == today and active:
                # Schedule is reset after deactivation since it is now entirely in the past
                service.system_update(
                    subscriber["_id"],
                    {
                        "is_active": False,
                        "schedule": {
                            "start_date": None,
                            "end_date": None,
                        },
                    },
                    subscriber,
                )
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' deactivated (end_date: {end})"
                )

    except Exception:
        logger.exception("[Subscribers Schedule]: Failed to update subscriber activation states based on schedule.")
