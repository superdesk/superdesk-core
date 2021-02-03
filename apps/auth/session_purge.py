# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from superdesk import app
from datetime import timedelta
from superdesk.utc import utcnow
from eve.utils import date_to_str
from superdesk import get_resource_service
import logging

logger = logging.getLogger(__name__)


class RemoveExpiredSessions(superdesk.Command):
    """Remove expired sessions from db.

    Using ``SESSION_EXPIRY_MINUTES`` config.

    Example:
    ::

        $ python manage.py session:gc

    """

    def run(self):
        self.remove_expired_sessions()

    def remove_expired_sessions(self):
        auth_service = get_resource_service("auth")
        expiry_minutes = app.settings["SESSION_EXPIRY_MINUTES"]
        expiration_time = utcnow() - timedelta(minutes=expiry_minutes)
        logger.info("Deleting session not updated since {}".format(expiration_time))
        query = {"_updated": {"$lte": date_to_str(expiration_time)}}
        sessions = auth_service.get(req=None, lookup=query)
        for session in sessions:
            auth_service.delete({"_id": str(session["_id"])})
        self._update_online_users()

    def _update_online_users(self):
        online_users = self._get_online_users()
        active_sessions_ids = self._get_active_session_ids()
        for user in online_users:
            session_preferences = user.get("session_preferences", {})
            active = {_id: data for _id, data in session_preferences.items() if active_sessions_ids.get(_id)}
            if len(active) != len(session_preferences):
                get_resource_service("users").system_update(user["_id"], {"session_preferences": active}, user)

    def _get_active_session_ids(self):
        active_sessions = get_resource_service("auth").get(req=None, lookup={})
        return {str(sess["_id"]): True for sess in active_sessions}

    def _get_online_users(self):
        return get_resource_service("users").get_from_mongo(
            None, {"session_preferences": {"$exists": True, "$nin": [None, {}]}}
        )
