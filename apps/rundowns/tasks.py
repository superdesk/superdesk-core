import pytz
import logging
import dateutil.rrule as rrule

from flask import current_app as app
from datetime import datetime, timedelta
from superdesk.celery_app import celery
from superdesk.utc import utc_to_local, local_to_utc
from superdesk.lock import lock, unlock
from apps.rundowns.types import IRRule

from . import templates, rundowns


logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=300)
def create_scheduled_rundowns() -> None:
    lock_id = "rundowns-create-scheduled-rundowns"
    templates_service = templates.templates_service
    if not lock(lock_id, expire=300):
        return
    try:
        logger.info("Checking templates for automatic rundown creation")
        tz = pytz.timezone(app.config["RUNDOWNS_TIMEZONE"])
        now = datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)
        buffer = timedelta(hours=app.config["RUNDOWNS_SCHEDULE_HOURS"])
        lookup = {"scheduled_on": {"$lt": now + buffer}, "repeat": True, "schedule.freq": {"$exists": True}}
        for template in templates_service.find(where=lookup):
            updates = {}
            local_date = utc_to_local(str(tz), template["scheduled_on"])
            logger.info("Creating Rundown for template %s on %s", template["title"], local_date.isoformat())
            rundowns.rundowns_service.create_from_template(
                template, local_date.date(), scheduled_on=template["scheduled_on"]
            )
            schedule: IRRule = template["schedule"]
            assert hasattr(rrule, schedule["freq"].upper())
            dates = list(
                rrule.rrule(
                    freq=getattr(rrule, schedule["freq"].upper()),
                    interval=schedule.get("interval", 1),
                    bymonth=schedule.get("by_month"),
                    bymonthday=schedule.get("by_month_day"),
                    byweekday=schedule.get("by_day"),
                    byweekno=schedule.get("by_week_no"),
                    dtstart=local_date,
                    count=10,
                )
            )
            for date in dates:
                if date > template["scheduled_on"] and date > now:
                    logger.info("Scheduling next Rundown for template %s on %s", template["title"], date.isoformat())
                    updates["scheduled_on"] = local_to_utc(str(tz), date)
                    break
            else:
                logger.warn("Could not schedule next Rundown for template %s", template["title"])

            if updates:
                templates_service.system_update(template["_id"], updates, template)
    finally:
        unlock(lock_id)
        logger.info("Done")
