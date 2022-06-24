import pytz
import logging
import superdesk
import dateutil.rrule as rrule

from datetime import datetime, timedelta
from flask import current_app as app
from superdesk.celery_app import celery
from superdesk.utc import utc_to_local, local_to_utc
from superdesk.lock import lock, unlock, get_host

from . import create


logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=300)
def create_scheduled_rundowns():
    lock_id = "rundowns-create-scheduled-rundowns"
    if not lock(lock_id, expire=300):
        return
    try:
        tz = pytz.timezone(app.config["RUNDOWNS_TIMEZONE"])
        now = datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)
        buffer = timedelta(hours=app.config["RUNDOWNS_SCHEDULE_HOURS"])
        lookup = {"scheduled_on": {"$lt": now + buffer}, "repeat": True, "schedule.freq": {"$exists": True}}
        templates_service = superdesk.get_resource_service("rundown_templates")
        for template in templates_service.find(where=lookup):
            updates = {}
            local_date = utc_to_local(str(tz), template["scheduled_on"])
            logger.info("Creating Rundown for template %s on %s", template["name"], local_date.isoformat())
            create.create_rundown_for_template(template, local_date.date(), template["scheduled_on"])
            schedule = template["schedule"]
            assert hasattr(rrule, schedule["freq"].upper())
            dates = list(
                rrule.rrule(
                    freq=getattr(rrule, schedule["freq"].upper()),
                    interval=schedule.get("interval", 1),
                    bymonth=schedule.get("month"),
                    bymonthday=schedule.get("monthday"),
                    byweekday=schedule.get("weekday"),
                    dtstart=local_date,
                    count=10,
                )
            )
            for date in dates:
                if date > template["scheduled_on"] and date > now:
                    logger.info("Scheduling next Rundown for template %s on %s", template["name"], date.isoformat())
                    updates["scheduled_on"] = local_to_utc(str(tz), date)
                    break
            else:
                logger.warn("Could not schedule next Rundown for template %s", template["name"])

            if updates:
                templates_service.system_update(template["_id"], updates, template)
    finally:
        unlock(lock_id)
