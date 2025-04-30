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
import superdesk
from superdesk.resource import Resource
from superdesk.eve_async import AsyncBaseService
from apps.auth.errors import CredentialsAuthError
from superdesk import get_resource_service


logger = logging.getLogger(__name__)


class ChangePasswordResource(Resource):
    schema = {
        "username": {"type": "string", "required": True},
        "old_password": {"type": "string", "required": True},
        "new_password": {"type": "string", "required": True},
    }
    public_methods = ["POST"]
    resource_methods = ["POST"]
    item_methods = []


class ChangePasswordService(AsyncBaseService):
    async def create_async(self, docs, **kwargs):
        for doc in docs:
            username = doc["username"]
            credentials = {"username": username, "password": doc["old_password"]}
            try:
                await get_resource_service("auth_db").authenticate(credentials, True)
            except Exception as e:
                raise CredentialsAuthError(credentials=credentials, error=e)

            users_service = superdesk.get_resource_service("users")
            user = await users_service.find_one_async(req=None, username=username)
            await users_service.update_password(user["_id"], doc["new_password"])
            del doc["old_password"]
            del doc["new_password"]

            # return etag for further user updates
            user = await users_service.find_one_async(req=None, _id=user["_id"])
            doc["_etag"] = user["_etag"]

            return [user["_id"]]
