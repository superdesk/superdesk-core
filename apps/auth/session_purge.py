# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from datetime import timedelta

from eve.utils import date_to_str

from superdesk.commands import cli
from superdesk.utc import utcnow
from superdesk import get_resource_service
from superdesk.core import get_app_config
from apps.auth.sessions import MOBILE_SESSION_TYPE


logger = logging.getLogger(__name__)


@cli.command("session:gc")
async def cli_session_gc():
    """Remove expired sessions from db.

    Using ``SESSION_EXPIRY_MINUTES`` config, or ``MOBILE_SESSION_EXPIRY_MINUTES`` for sessions created by
    mobile pairing. Also removes expired mobile pairing requests.

    Example:
    ::

        $ python manage.py session:gc

    """

    await RemoveExpiredSessions().run()


class RemoveExpiredSessions:
    async def run(self):
        await self.remove_expired_sessions()
        await self.remove_expired_mobile_pairings()

    async def remove_expired_sessions(self):
        now = utcnow()
        web_expiration_time = now - timedelta(minutes=get_app_config("SESSION_EXPIRY_MINUTES"))
        mobile_expiration_time = now - timedelta(minutes=get_app_config("MOBILE_SESSION_EXPIRY_MINUTES"))
        logger.info(
            "Deleting sessions not updated since {} (mobile sessions since {})".format(
                web_expiration_time, mobile_expiration_time
            )
        )
        await self._remove_sessions(
            {"session_type": {"$ne": MOBILE_SESSION_TYPE}, "_updated": {"$lte": date_to_str(web_expiration_time)}}
        )
        await self._remove_sessions(
            {"session_type": MOBILE_SESSION_TYPE, "_updated": {"$lte": date_to_str(mobile_expiration_time)}}
        )
        await self._update_online_users()

    async def _remove_sessions(self, query):
        auth_service = get_resource_service("auth")
        sessions = await (await auth_service.get_async(req=None, lookup=query)).to_list()
        if sessions:
            await auth_service.delete_docs_async(sessions)

    async def remove_expired_mobile_pairings(self):
        # The resource is not registered when the feature is off.
        if get_app_config("MOBILE_PAIRING_ENABLED"):
            await get_resource_service("mobile_pairing").remove_expired()

    async def _update_online_users(self):
        online_users = await self._get_online_users()
        active_sessions_ids = await self._get_active_session_ids()
        async for user in online_users:
            session_preferences = user.get("session_preferences", {})
            active = {_id: data for _id, data in session_preferences.items() if active_sessions_ids.get(_id)}
            if len(active) != len(session_preferences):
                await get_resource_service("users").system_update_async(
                    user["_id"], {"session_preferences": active}, user
                )

    async def _get_active_session_ids(self):
        active_sessions = await get_resource_service("auth").get_async(req=None, lookup={})
        return {str(sess["_id"]): True async for sess in active_sessions}

    async def _get_online_users(self):
        return await get_resource_service("users").get_from_mongo_async(
            None, {"session_preferences": {"$exists": True, "$nin": [None, {}]}}
        )
