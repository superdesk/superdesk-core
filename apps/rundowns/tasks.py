import pytz
import superdesk
import dateutil.rrule as rrule

from datetime import datetime, timedelta
from flask import current_app as app
from superdesk.celery_app import celery
from superdesk.utc import utc_to_local, local_to_utc
from superdesk.lock import lock, unlock

from . import utils, create


@celery.task(soft_time_limit=300)
def create_scheduled_rundowns():
    lock_id = "rundowns:create-scheduled-rundowns"
    if not lock(lock_id, 300):
        return
    try:
        archive_service = superdesk.get_resource_service("archive")
        templates_service = superdesk.get_resource_service("rundown_templates")

        now = datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)
        lookup = {"schedule.is_active": True, "airtime_time": {"$exists": True}}
        for template in templates_service.find(where=lookup):
            airtime = utils.parse_time(template["airtime_time"])
            start_date = utc_to_local(
                app.config["RUNDOWNS_TIMEZONE"],
                template.get("last_scheduled", template.get("_created", datetime.utcnow())),
            ).replace(hour=airtime.hour, minute=airtime.minute, second=airtime.second, microsecond=0)
            schedule = template["schedule"]
            assert hasattr(rrule, schedule["freq"].upper())
            dates = list(
                rrule.rrule(
                    freq=getattr(rrule, schedule["freq"].upper()),
                    interval=schedule.get("interval", 1),
                    bymonth=schedule.get("month"),
                    bymonthday=schedule.get("monthday"),
                    byweekday=schedule.get("weekday"),
                    dtstart=start_date,
                    count=3,
                )
            )
            updates = {}
            for date in dates:
                if date <= now:
                    continue

                if date - now > timedelta(hours=24):
                    continue

                # store for next time
                updates["last_scheduled"] = local_to_utc(app.config["RUNDOWNS_TIMEZONE"], date)

                existing = archive_service.find_one(
                    req=None, rundown_template=template["_id"], airtime_date=date.date().isoformat()
                )
                if existing is not None:
                    break

                create.create_rundown_for_template(template, date.date())

            if updates:
                templates_service.system_update(template["_id"], updates, template)
    finally:
        unlock(lock_id)
