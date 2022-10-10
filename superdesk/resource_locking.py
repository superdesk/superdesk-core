import enum
import flask
import datetime

from flask_babel import _

from superdesk.utc import utcnow


LOCK_HOURS = 4


class LockActions(enum.Enum):
    UNLOCK = "unlock"
    LOCK = "lock"
    FORCE_LOCK = "force-lock"


LOCKED_ACTIONS = [LockActions.LOCK.value, LockActions.FORCE_LOCK.value]
UNLOCKED_ACTIONS = [LockActions.UNLOCK.value]


def on_update(updates: dict, original: dict):
    from apps.auth import get_auth

    now = utcnow()
    ttl = now + datetime.timedelta(hours=LOCK_HOURS)
    auth = get_auth()

    # check the lock if present
    if is_locked(original, now):
        if updates.get("_lock_action") == LockActions.FORCE_LOCK.value:
            pass  # force locking, might need specific permissions eventually
        elif auth["_id"] != original.get("_lock_session"):
            flask.abort(412, description=_("Resource is locked."))

    # lock
    if updates.get("_lock_action") in LOCKED_ACTIONS:
        auth = get_auth()
        updates.update(
            _lock=True,
            _lock_user=auth["user"],
            _lock_session=auth["_id"],
            _lock_time=now,
            _lock_expiry=ttl,
        )

    # unlock
    if updates.get("_lock_action") in UNLOCKED_ACTIONS:
        updates.update(
            _lock=False,
            _lock_user=None,
            _lock_session=None,
            _lock_time=None,
            _lock_expiry=None,
        )


def is_locked(item, now: datetime.datetime) -> bool:
    return item.get("_lock") and item.get("_lock_expiry") > now
