from typing import cast
import pytz
import logging
from datetime import datetime, tzinfo

from superdesk.core import get_app_config
from superdesk.celery_app import celery
from superdesk.utc import utc_to_local, utcnow
from superdesk.lock import lock, unlock
from apps.rundowns.types import IRRule

from . import templates, rundowns, utils


logger = logging.getLogger(__name__)


@celery.task(soft_time_limit=300)
def create_scheduled_rundowns() -> None:
    lock_id = "rundowns-create-scheduled-rundowns"
    if not lock(lock_id, expire=300):
        return
    logger.info("Starting to create scheduled rundowns")
    try:
        now = utcnow()
        tz = pytz.timezone(cast(str, get_app_config("RUNDOWNS_TIMEZONE")))
        create_scheduled(now, tz)
    finally:
        unlock(lock_id)
        logger.info("Done creating scheduled rundowns")


def create_scheduled(now: datetime, tz: tzinfo):
    lookup = {"autocreate_on": {"$lte": now}, "repeat": True, "schedule.freq": {"$exists": True}}
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
            try:
                rundowns.rundowns_service.create_from_template(
                    template, local_date, scheduled_on=template["scheduled_on"]
                )
            except Exception as err:
                logger.exception(err)
        else:
            logger.info("Rundown already exists for template %s on %s", template["title"], local_date.isoformat())
        schedule: IRRule = template["schedule"]
        next_date = utils.get_next_date(schedule, local_date)
        if not next_date:
            logger.warn("Could not schedule next Rundown for template %s", template["title"])
            updates["repeat"] = False
        else:
            logger.info("Scheduling next Rundown for template %s on %s", template["title"], next_date.isoformat())
            utils.set_autocreate_schedule(updates, next_date, template)
        if updates:
            templates.templates_service.system_update(template["_id"], updates, template)
