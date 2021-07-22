# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
from flask import request, current_app as app
from flask_babel import _
from eve.utils import config

from superdesk import utils as utils, get_resource_service, get_resource_privileges
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from superdesk.users.errors import UserInactiveError
from superdesk.utc import utcnow
from apps import auth
from apps.auth.errors import UserDisabledError


class AuthService(BaseService):
    def authenticate(self, document):
        """Authenticate user according to credentials

        :param documents: credentials for this authentication mechanism
        :return: authenticated user
        :raise: CredentialsAuthError if authentication is invalid
        """
        raise NotImplementedError()

    def on_create(self, docs):
        for doc in docs:
            user = self.authenticate(doc)
            if not user:
                raise ValueError()
            if "is_enabled" in user and not user.get("is_enabled", False):
                raise UserDisabledError()
            if not user.get("is_active", False):
                raise UserInactiveError()
            self.set_auth_default(doc, user["_id"])

    def on_created(self, docs):
        for doc in docs:
            get_resource_service("preferences").set_session_based_prefs(doc["_id"], doc["user"])
            self.set_user_last_activity(doc["user"])

    def set_user_last_activity(self, user_id, done=False):
        now = utcnow()
        user_service = get_resource_service("users")
        user = user_service.find_one(req=None, _id=user_id)
        user_service.system_update(
            user["_id"],
            {"last_activity_at": now if not done else None, "_updated": now},
            user,
        )

    def set_auth_default(self, doc, user_id):
        doc["user"] = user_id
        doc["token"] = utils.get_random_string(40)
        doc.pop("password", None)

    def update_session(self, updates=None):
        """Update current session with given data.

        :param updates: updates to be made
        """
        if not updates:
            updates = {}
        self.system_update(flask.g.auth["_id"], updates, flask.g.auth)

    def on_fetched_item(self, doc: dict) -> None:
        if str(doc["user"]) != str(auth.get_user_id()):
            raise SuperdeskApiError.notFoundError(_("Not found."))

    def on_deleted(self, doc):
        """Runs on delete of a session

        :param doc: A deleted auth doc AKA a session
        :return:
        """
        # notify that the session has ended
        app.on_session_end(doc["user"], doc["_id"])
        self.set_user_last_activity(doc["user"], done=True)

    def is_authorized(self, **kwargs) -> bool:
        """
        Check auth for intrinsic methods.
        """
        method = kwargs["method"]
        user = auth.get_user()

        # delete token is a part of `users` privelege
        # user with `users` privelege can delete sessions of any user
        # user without `users` privelege can delete only it's own session (logout)
        if method == "DELETE":
            _auth = self.find_one(req=None, _id=kwargs.get("_id"))
            if _auth and _auth.get("user") == user.get("_id"):
                return True

            active_privileges = user.get("active_privileges", {})
            users_resource_privileges = get_resource_privileges("users").get(method, None)
            return active_privileges.get(users_resource_privileges, False)

        return True


class UserSessionClearService(BaseService):
    def delete(self, lookup):
        """Delete user session.

        Deletes all the records from auth and corresponding
        session_preferences from user collections
        If there are any orphan session_preferences exist they get deleted as well
        """
        users_service = get_resource_service("users")
        user_id = request.view_args["user"]
        user = users_service.find_one(req=None, _id=user_id)
        sessions = get_resource_service("auth").get(req=None, lookup={"user": user_id})

        error_message = self.__can_clear_sessions(user)
        if error_message:
            raise SuperdeskApiError.forbiddenError(message=error_message)

        # Delete all the sessions
        for session in sessions:
            get_resource_service("auth").delete_action({config.ID_FIELD: str(session[config.ID_FIELD])})

        # Check if any orphan session_preferences exist for the user
        if user.get("session_preferences"):
            # Delete the orphan sessions
            users_service.patch(user[config.ID_FIELD], {"session_preferences": {}})

        return [{"complete": True}]

    def __can_clear_sessions(self, user):
        """Checks if the session clear request is Invalid.

        Operation is invalid if one of the below is True:
            1. Check if the user exists.
            2. Check if the user is clearing his/her own sessions.

        :return: error message if invalid.
        """

        if not user:
            return "Invalid user to clear sessions."

        if str(user[config.ID_FIELD]) == str(flask.g.user[config.ID_FIELD]):
            return "Not allowed to clear your own sessions."
