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
import logging
import datetime
from superdesk.utc import utcnow
from eve.utils import date_to_str, ParsedRequest, config
from copy import deepcopy

logger = logging.getLogger(__name__)


class PurgeAudit(superdesk.Command):
    """
    Purges the Monogo audit collection, entries are purged if the related item is no longer in
     'Production'. Other entries are deleted after the configured time period.
    """

    # The list of resource entries that we will preseved in audit if an associated item still exists in production
    item_resources = [
        "archive_lock",
        "archive_unlock",
        "fetch",
        "archive",
        "move",
        "publish_queue",
        "archive_publish",
        "archive_resend",
        "archive_rewrite",
        "duplicate",
        "archive_link",
        "item_comments",
        "marked_for_highlights",
        "archive_broadcast",
        "archived",
        "copy",
        "ingest"
    ]

    # A query that identifies the entries in the audit collection that relate to content items.
    item_entry_query = {'$and': [{'resource': {'$in': item_resources}},
                                 {'audit_id': {'$ne': None}}, {'audit_id': {'$ne': ''}}]}

    not_item_entry_query = {'$or': [{'resource': {'$nin': item_resources}},
                                    {'audit_id': {'$in': [None, '']}}]}

    option_list = (
        superdesk.Option('--expiry_minutes', '-e', dest='expiry', required=False),
    )

    def run(self, expiry=None):
        if expiry is not None:
            self.expiry = utcnow() - datetime.timedelta(minutes=int(expiry))
        else:
            if config.AUDIT_EXPIRY_MINUTES == 0:
                logger.info('Audit purge is not enabled')
                return
            self.expiry = utcnow() - datetime.timedelta(minutes=config.AUDIT_EXPIRY_MINUTES)
        logger.info("Starting audit purge for items older than {}".format(self.expiry))
        self.purge_orphaned_item_audits()
        self.purge_old_entries()
        logger.info("Completed audit purge")

    def _get_archive_ids(self, ids):
        """
        Given a set of ids return those that have an entry in the archive collection
        :param ids:
        :return:
        """
        service = superdesk.get_resource_service('archive')
        query = {'_id': {'$in': list(ids)}}
        req = ParsedRequest()
        req.projection = '{"_id": 1}'
        archive_ids = service.get_from_mongo(req=req, lookup=query)
        existing = list([item['_id'] for item in archive_ids])
        return set(existing)

    def purge_orphaned_item_audits(self):
        """
        Purge the audit items that do not have associated entries existing in archive
        :return:
        """
        service = superdesk.get_resource_service('audit')
        current_id = None
        logger.info('Starting to purge audit logs of content items not in archive at {}'.format(utcnow()))

        # Scan the audit collection for items to delete
        while True:
            query = deepcopy(self.item_entry_query)
            query['$and'].append({'_updated': {'$lte': date_to_str(self.expiry)}})
            if current_id:
                query['$and'].append({'_id': {'$gt': current_id}})
            req = ParsedRequest()
            req.sort = '[("_id", 1)]'
            req.projection = '{"_id": 1, "audit_id":1}'
            req.max_results = 1000
            audits = service.get_from_mongo(req=req, lookup=query)
            items = list([(item['_id'], item['audit_id']) for item in audits])
            if len(items) == 0:
                logger.info('Finished purging audit logs of content items not in archive at {}'.format(utcnow()))
                return
            logger.info('Found {} orphaned audit items at {}'.format(len(items), utcnow()))
            current_id = items[len(items) - 1][0]

            batch_ids = set([i[1] for i in items])
            archive_ids = self._get_archive_ids(batch_ids)
            ids = (batch_ids - archive_ids)
            audit_ids = [i[0] for i in items if i[1] in ids]
            logger.info('Deleting {} orphaned audit items at {}'.format(len(audit_ids), utcnow()))
            service.delete_ids_from_mongo(audit_ids)

    def purge_old_entries(self):
        """
        Purge entries older than the expiry that are not related to archive items
        :return:
        """
        service = superdesk.get_resource_service('audit')
        current_id = None
        logger.info('Starting to purge audit logs of none content items at {}'.format(utcnow()))

        while True:
            lookup = {'$and': [self.not_item_entry_query, {'_updated': {'$lte': date_to_str(self.expiry)}}]}
            if current_id:
                lookup['$and'].append({'_id': {'$gt': current_id}})
            req = ParsedRequest()
            req.sort = '[("_id", 1)]'
            req.projection = '{"_id": 1}'
            req.max_results = 1000
            audits = service.get_from_mongo(req=req, lookup=lookup)
            items = list(item.get('_id') for item in audits)
            if len(items) == 0:
                logger.info('Finished purging audit logs of none content items at {}'.format(utcnow()))
                return
            logger.info('Found {} audit items at {}'.format(len(items), utcnow()))
            current_id = items[len(items) - 1]
            logger.info('Deleting {} old audit items'.format(len(items)))
            service.delete_ids_from_mongo(items)


superdesk.command('audit:purge', PurgeAudit())
