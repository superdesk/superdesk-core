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

        tz = pytz.timezone(app.config["RUNDOWNS_TIMEZONE"])
        now = datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)
        lookup = {"schedule.is_active": True, "airtime_time": {"$exists": True}}
        for template in templates_service.find(where=lookup):
            start_time = utils.parse_time(template["airtime_time"])
            start_date = utils.parse_date(template["airtime_date"]) if template.get("airtime_date") else None
            if template.get("last_scheduled"):
                start_date = utc_to_local(str(tz), template["last_scheduled"]).date()
            if start_date is None:
                start_date = datetime.now(tz=tz).date()
            dtstart = utils.combine_date_time(start_date, start_time, tz=tz)
            schedule = template["schedule"]
            assert hasattr(rrule, schedule["freq"].upper())
            dates = list(
                rrule.rrule(
                    freq=getattr(rrule, schedule["freq"].upper()),
                    interval=schedule.get("interval", 1),
                    bymonth=schedule.get("month"),
                    bymonthday=schedule.get("monthday"),
                    byweekday=schedule.get("weekday"),
                    dtstart=dtstart,
                    count=3,
                )
            )
            updates = {}
            for date in dates:
                if date <= now:
                    continue

                if date - now > timedelta(hours=app.config["RUNDOWNS_SCHEDULE_HOURS"]):
                    continue

                # valid time, on next run start from there
                updates["last_scheduled"] = local_to_utc(str(tz), date)

                existing = archive_service.find_one(
                    req=None, rundown_template=template["_id"], airtime_date=date.date().isoformat()
                )
                if existing is None:
                    create.create_rundown_for_template(template, date.date())

            if updates:
                templates_service.system_update(template["_id"], updates, template)
    finally:
        unlock(lock_id)
