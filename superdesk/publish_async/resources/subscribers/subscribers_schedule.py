import logging

from superdesk.celery_app import celery
from superdesk.dates import get_local_today
from .service import SubscribersService

logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=30)
async def update_subscriber_activation_states():
    """Task to activate/deactivate subscribers whose startDate or endDate matches current today"""
    today = get_local_today().date().isoformat()
    service = SubscribersService()

    try:
        # Query for subscribers that have a schedule defined for current date
        lookup = {
            "$or": [
                {"schedule.start_date": today},
                {"schedule.end_date": today},
            ]
        }
        cursor = await service.search(lookup)
        subscribers = await cursor.to_list_raw()
        logger.info(
            "[Subscribers Schedule]: Processing %d subscribers for schedule activation/deactivation", len(subscribers)
        )

        for subscriber in subscribers:
            schedule = subscriber.get("schedule") or {}
            start = schedule.get("start_date")
            end = schedule.get("end_date")
            active = subscriber.get("is_active", False)

            if start == today and not active:
                await service.system_update(subscriber["_id"], {"is_active": True})
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' activated (start_date: {start})"
                )
            elif end == today and active:
                # Schedule is reset after deactivation since it is now entirely in the past
                await service.system_update(
                    subscriber["_id"],
                    {
                        "is_active": False,
                        "schedule": {
                            "start_date": None,
                            "end_date": None,
                        },
                    },
                )
                logger.info(
                    f"[Subscribers Schedule]: Subscriber '{subscriber.get('name', subscriber['_id'])}' deactivated (end_date: {end})"
                )

    except Exception:
        logger.exception("[Subscribers Schedule]: Failed to update subscriber activation states based on schedule.")
