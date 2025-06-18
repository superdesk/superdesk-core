import pytz
from datetime import datetime
from superdesk.core import get_config


def get_local_today() -> datetime:
    tz = pytz.timezone(get_config(str, "DEFAULT_TIMEZONE"))
    return datetime.now(tz)
