import datetime
import dateutil.rrule as rrule

from typing import Optional


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


def get_next_date(start_date: datetime.datetime, schedule) -> Optional[datetime.datetime]:
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
        if date > now and date > start_date:
            print("DATE", date, start_date)
            return date
    return None
