import logging

from superdesk import get_resource_service
from superdesk.celery_app import celery
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=30)
def update_subscriber_activation_states():
    """Celery task to check scheduled subscribers and activate/deactivate them.

    Runs every minute. If a subscriber has a `schedule` field defined,
    this will check if the current time is within the start and end range
    and update `is_active` accordingly.
    """
    now = utcnow()
    service = get_resource_service("subscribers")

    try:
        # Query for subscribers that have a schedule defined
        lookup = {
            "$and": [
                {"schedule.startDate": {"$ne": None}},
                {"schedule.endDate": {"$ne": None}},
            ]
        }
        subscribers = list(service.get(req=None, lookup=lookup))
        logger.info("Processing %d subscribers for schedule activation/deactivation", len(subscribers))

        for subscriber in subscribers:
            updated = False
            schedule = subscriber.get("schedule") or {}
            start = schedule.get("startDate")
            end = schedule.get("endDate")
            active = subscriber.get("is_active", False)


            # Determine desired state
            should_be_active = (
                (not start or now >= start) and
                (not end or now <= end)
            )

            if should_be_active != active:
                service.system_update(
                    subscriber["_id"],
                    {"is_active": should_be_active},
                    subscriber
                )
                updated = True

            if updated:
                message = (
                    f"Subscriber '{subscriber.get('name', subscriber['_id'])}' "
                    f"{'activated' if should_be_active else 'deactivated'} "
                    f"due to schedule. Start: {start}, End: {end}"
                )
                logger.info(message)

    except Exception as e:
        print(f"[subscribers_schedule] Error occurred: {e}")
        logger.exception("Failed to update subscriber activation states based on schedule.")
