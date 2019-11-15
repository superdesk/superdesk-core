# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk import get_resource_service
from superdesk.services import Service
from superdesk.notification import push_notification
from superdesk.errors import SuperdeskApiError
from eve.utils import config
from eve.utils import ParsedRequest
from flask_babel import _
from copy import deepcopy


class ContactsService(Service):

    def get(self, req, lookup):

        # by default the response will have the inactive and not public entries filtered out
        if 'all' not in req.args:
            lookup['is_active'] = True
            lookup['public'] = True
        return super().get(req, lookup)

    def on_create(self, docs):
        for doc in docs:
            self._validate_assignable(doc)

    def on_created(self, docs):
        """
        Send notification to clients that new contact(s) have been created
        :param docs:
        :return:
        """
        push_notification('contacts:create', _id=[doc.get(config.ID_FIELD) for doc in docs])

    def on_update(self, updates, original):
        item = deepcopy(original)
        item.update(updates)
        self._validate_assignable(item)

    def on_updated(self, updates, original):
        """
        Send notifification to clients that a contact has been updated
        :param updates:
        :param original:
        :return:
        """
        push_notification('contacts:update', _id=[original.get(config.ID_FIELD)])

    def on_deleted(self, doc):
        """
        Send a notification to clients that a contact has been deleted
        :param doc:
        :return:
        """
        push_notification('contacts:deleted', _id=[doc.get(config.ID_FIELD)])

    def _validate_assignable(self, contact):
        """Validates a required email address if the contact_type has assignable flag turned on"""

        if not contact or not contact.get('contact_type'):
            return

        types = get_resource_service('vocabularies').find_one(req=None, _id='contact_type')

        if not types:
            return

        contact_type = next((
            item
            for item in (types.get('items') or [])
            if item.get('qcode') == contact.get('contact_type')
        ), None)

        if not contact_type or not contact_type.get('assignable'):
            return

        if not contact.get('contact_email'):
            raise SuperdeskApiError.badRequestError(
                message=_("Contacts of type \"{contact_type}\" must have an email address").format(
                    contact_type=contact_type.get('name')
                )
            )


class OrganisationService(Service):
    def get(self, req, lookup):
        """
        Search for organisation matching the passed q parameter
        :param req:
        :param lookup:
        :return: List of matching organisation strings
        """
        new_req = ParsedRequest()

        q_str = 'organisation:' + '* organisation:'.join(req.args.get('q', '').split()) + '*'
        new_req.args = {'q': q_str, 'default_operator': 'AND', 'projections': '{"organisation": 1}'}
        ret = super().get(new_req, lookup)

        # Remove any duplicate entries from the response
        orgs = []
        de_duped = []
        for d in ret.docs:
            if d.get('organisation') not in orgs:
                orgs.append(d.get('organisation'))
                de_duped.append(d)
        ret.docs = de_duped
        ret.hits['hits']['total'] = len(ret.docs)
        return ret
