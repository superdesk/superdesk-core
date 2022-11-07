import logging
import datetime
import dateutil.rrule as rrule

from typing import Optional
from flask import current_app as app

from superdesk.utc import utcnow, utc_to_local, local_to_utc

from . import types

logger = logging.getLogger(__name__)


def parse_time(timestr: str) -> datetime.time:
    return datetime.time.fromisoformat(timestr).replace(microsecond=0)


def parse_date(datestr: str) -> datetime.date:
    return datetime.date.fromisoformat(datestr)


def combine_date_time(
    date: datetime.date, time: datetime.time, tz: Optional[datetime.tzinfo] = None
) -> datetime.datetime:
    return datetime.datetime(
        year=date.year,
        month=date.month,
        day=date.day,
        hour=time.hour,
        minute=time.minute,
        second=time.second,
        tzinfo=tz if tz is not None else time.tzinfo,
        microsecond=0,
    )


def to_utc(date: datetime.datetime) -> datetime.datetime:
    local = local_to_utc(app.config["RUNDOWNS_TIMEZONE"], date)
    assert local is not None
    return local


def get_start_datetime(time: datetime.time, date: Optional[datetime.date]) -> datetime.datetime:
    now = utcnow()
    local_now = utc_to_local(app.config["RUNDOWNS_TIMEZONE"], now)
    if date is None or date < local_now.date():
        date = local_now.date()
    return combine_date_time(date, time, local_now.tzinfo)


def get_next_date(schedule, start_date: datetime.datetime, include_start=False) -> Optional[datetime.datetime]:
    assert start_date.tzinfo is not None, "start_date must be time zone aware"
    if not schedule.get("freq"):
        return None
    freq = schedule.get("freq", "DAILY").upper()
    assert hasattr(rrule, freq), "Unknown frequency {}".format(freq)
    now = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).replace(microsecond=0)
    dates = list(
        rrule.rrule(
            freq=getattr(rrule, freq),
            interval=schedule.get("interval", 1),
            bymonth=schedule.get("by_month"),
            bymonthday=schedule.get("by_month_day"),
            byweekday=schedule.get("by_day"),
            byweekno=schedule.get("by_week_no"),
            dtstart=start_date.replace(microsecond=0),
            count=10,
        )
    )
    for date in dates:
        if date > now and (include_start or date > start_date):
            return date
    return None


def set_autocreate_schedule(updates, local_date: Optional[datetime.datetime], template):
    if local_date is None:
        logger.warning("Could not schedule next Rundown for template %s", template["title"])
        updates["scheduled_on"] = updates["autocreate_on"] = None
        return

    create_before = (
        datetime.timedelta(seconds=template["autocreate_before_seconds"])
        if template.get("autocreate_before_seconds")
        else (datetime.timedelta(hours=app.config["RUNDOWNS_SCHEDULE_HOURS"]))
    )

    updates["scheduled_on"] = to_utc(local_date)
    updates["autocreate_on"] = updates["scheduled_on"] - create_before

    logger.info("Next rundown for template %s scheduled on %s", template["title"], updates["scheduled_on"].isoformat())


def item_title(show: types.IShow, rundown: types.IRundown, item: types.IRundownItem, with_camera=True) -> str:
    if item.get("item_type") and item["item_type"].upper() in ("PRLG", "AACC"):
        pieces = [
            item["item_type"],
            show.get("shortcode"),
            (item.get("title") or "").replace(" ", "-"),
        ]
        if with_camera and item.get("camera"):
            pieces.extend(item["camera"])
        return "-".join(
            filter(
                None,
                pieces,
            )
        ).upper()
    return (item.get("title") or "").upper()