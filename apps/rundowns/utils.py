import datetime
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
