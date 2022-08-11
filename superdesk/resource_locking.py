import flask
import datetime

from flask_babel import _

from superdesk.utc import utcnow


LOCK_HOURS = 4


def on_update(updates: dict, original: dict):
    from apps.auth import get_auth

    now = utcnow()
    auth = get_auth()

    # check the lock if present
    if is_locked(original, now):
        if auth["_id"] != original.get("_lock_session"):
            flask.abort(412, description=_("Resource is locked."))

    # lock
    if updates.get("_lock"):
        auth = get_auth()
        updates.update(
            _lock_user=auth["user"],
            _lock_session=auth["_id"],
            _lock_time=utcnow(),
        )

    # unlock
    if updates.get("_lock") is False:
        updates.update(
            _lock_user=None,
            _lock_session=None,
            _lock_time=None,
        )


def is_locked(item, now: datetime.datetime) -> bool:
    return item.get("_lock") and now - item["_lock_time"] < datetime.timedelta(hours=LOCK_HOURS)
