# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.resource_fields import ID_FIELD
from superdesk.notification import push_notification
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from superdesk.eve_async import AsyncBaseService
from eve.utils import ParsedRequest
from quart_babel import gettext as _
from copy import deepcopy


class ContactsService(AsyncBaseService):
    async def get_async(self, req, lookup):
        # by default the response will have the inactive entries filtered out
        if "all" not in req.args:
            lookup["is_active"] = True

        return await super().get_async(req, lookup)

    async def on_create_async(self, docs):
        for doc in docs:
            await self._validate_assignable(doc)

    async def on_created_async(self, docs):
        """
        Send notification to clients that new contact(s) have been created
        :param docs:
        :return:
        """
        push_notification("contacts:create", _id=[doc.get(ID_FIELD) for doc in docs])

    async def on_update_async(self, updates, original):
        item = deepcopy(original)
        item.update(updates)
        await self._validate_assignable(item)

    async def on_updated_async(self, updates, original):
        """
        Send notifification to clients that a contact has been updated
        :param updates:
        :param original:
        :return:
        """
        push_notification("contacts:update", _id=[original.get(ID_FIELD)])

    async def on_deleted_async(self, doc):
        """
        Send a notification to clients that a contact has been deleted
        :param doc:
        :return:
        """
        push_notification("contacts:deleted", _id=[doc.get(ID_FIELD)])

    async def _validate_assignable(self, contact):
        """Validates a required email address if the contact_type has assignable flag turned on"""

        if not contact or not contact.get("contact_type"):
            return

        types = await get_resource_service("vocabularies").find_one_async(req=None, _id="contact_type")

        if not types:
            return

        contact_type = next(
            (item for item in (types.get("items") or []) if item.get("qcode") == contact.get("contact_type")), None
        )

        if not contact_type or not contact_type.get("assignable"):
            return

        if not contact.get("contact_email"):
            raise SuperdeskApiError.badRequestError(
                message=_('Contacts of type "{contact_type}" must have an email address').format(
                    contact_type=contact_type.get("name")
                )
            )


class OrganisationService(AsyncBaseService):
    async def get_async(self, req, lookup):
        """
        Search for organisation matching the passed q parameter
        :param req:
        :param lookup:
        :return: List of matching organisation strings
        """
        new_req = ParsedRequest()

        q_str = "organisation:" + "* organisation:".join(req.args.get("q", "").split()) + "*"
        new_req.args = {"q": q_str, "default_operator": "AND", "projections": '{"organisation": 1}'}
        ret = await super().get_async(new_req, lookup)

        # Remove any duplicate entries from the response
        orgs = []
        de_duped = []
        for d in ret.docs:
            if d.get("organisation") not in orgs:
                orgs.append(d.get("organisation"))
                de_duped.append(d)
        ret.docs = de_duped
        ret.hits["hits"]["total"] = len(ret.docs)
        return ret
