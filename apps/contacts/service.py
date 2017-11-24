# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from superdesk.services import Service
from superdesk.notification import push_notification
from eve.utils import config


class ContactsService(Service):

    def get(self, req, lookup):

        # by default the response will have the inactive and not public entries filtered out
        if 'all' not in req.args:
            lookup['is_active'] = True
            lookup['public'] = True
        return super().get(req, lookup)

    def on_created(self, docs):
        """
        Send notification to clients that new contact(s) have been created
        :param docs:
        :return:
        """
        push_notification('contacts:create', _id=[doc.get(config.ID_FIELD) for doc in docs])

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
