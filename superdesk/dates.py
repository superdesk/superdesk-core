import pytz

from flask import current_app as app
from datetime import datetime

def get_local_today() -> datetime:
    tz = pytz.timezone(app.config["DEFAULT_TIMEZONE"])
    return datetime.now(tz)
