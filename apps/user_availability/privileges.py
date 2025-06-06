import flask

from flask_babel import gettext

from apps.auth import get_user_id
from superdesk.types import Id
from superdesk.users.services import current_user_has_privilege


USER_AVAILABILITY_READ = "user_availability"
USER_AVAILABILITY_WRITE = "user_availability_manage"


def validate_user_can_manage_availability(modified_user_id: Id) -> None:
    current_user_id = get_user_id()

    if str(current_user_id) == str(modified_user_id):
        return

    if current_user_has_privilege(USER_AVAILABILITY_WRITE):
        return

    flask.abort(403, description=gettext("You can only modify your own availability settings."))
