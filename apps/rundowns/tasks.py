import pytz
import logging

from flask import current_app as app
from datetime import datetime, timedelta, tzinfo
from superdesk.celery_app import celery
from superdesk.utc import utc_to_local, local_to_utc, utcnow
from superdesk.lock import lock, unlock
from apps.rundowns.types import IRRule

from . import templates, rundowns, utils


logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=300)
def create_scheduled_rundowns() -> None:
    lock_id = "rundowns-create-scheduled-rundowns"
    if not lock(lock_id, expire=300):
        return
    try:
        now = utcnow()
        tz = pytz.timezone(app.config["RUNDOWNS_TIMEZONE"])
        populate_schedule(now, tz)
        create_scheduled(now, tz)
    finally:
        unlock(lock_id)
        logger.info("Done")


def populate_schedule(now: datetime, tz: tzinfo):
    logger.info("Set schedule where missing")
    local_now = utc_to_local(str(tz), now)
    lookup = {
        "scheduled_on": None,
        "repeat": True,
        "schedule.freq": {"$exists": True},
        "airtime_time": {"$exists": True},
    }
    for template in templates.templates_service.find(where=lookup):
        time = utils.parse_time(template["airtime_time"])
        start = local_now.replace(hour=time.hour, minute=time.minute, second=time.second)
        next_date = utils.get_next_date(start, template["schedule"])
        if not next_date:
            logger.warn("Could not schedule next Rundown for template %s", template["title"])
            continue
        else:
            logger.info("Next rundown for template %s scheduled on %s", template["title"], next_date.isoformat())
        updates = {"scheduled_on": local_to_utc(str(tz), next_date)}
        templates.templates_service.system_update(template["_id"], updates, template)


def create_scheduled(now: datetime, tz: tzinfo):
    logger.info("Create scheduled rundowns")
    buffer = timedelta(hours=app.config["RUNDOWNS_SCHEDULE_HOURS"])
    lookup = {"scheduled_on": {"$lt": now + buffer}, "repeat": True, "schedule.freq": {"$exists": True}}
    for template in templates.templates_service.find(where=lookup):
        updates = {}
        local_date = utc_to_local(str(tz), template["scheduled_on"])
        if (
            rundowns.rundowns_service.find_one(
                req=None, template=template["_id"], scheduled_on=template["scheduled_on"]
            )
            is None
        ):
            logger.info("Creating Rundown for template %s on %s", template["title"], local_date.isoformat())
            rundowns.rundowns_service.create_from_template(template, local_date, scheduled_on=template["scheduled_on"])
        else:
            logger.info("Rundown already exists for template %s on %s", template["title"], local_date.isoformat())
        schedule: IRRule = template["schedule"]
        next_date = utils.get_next_date(local_date, schedule)
        if not next_date:
            logger.warn("Could not schedule next Rundown for template %s", template["title"])
            updates["repeat"] = False
        else:
            logger.info("Scheduling next Rundown for template %s on %s", template["title"], next_date.isoformat())
            updates["scheduled_on"] = local_to_utc(str(tz), next_date)
        if updates:
            templates.templates_service.system_update(template["_id"], updates, template)
