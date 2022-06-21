import datetime


def parse_time(timestr: str) -> datetime.time:
    return datetime.time.fromisoformat(timestr).replace(microsecond=0)
