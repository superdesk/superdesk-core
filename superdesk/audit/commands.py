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
        "archive_autosave",
        "move",
        "publish_queue",
        "archive_publish",
        "archive_resend",
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
    item_entry_query = {'$and': [{'resource': {'$in': item_resources}}, {'extra': {'$exists': True}},
                                 {'$or': [{'extra.guid': {'$exists': True}},
                                          {'extra._id': {'$exists': True}},
                                          {'extra.item_id': {'$exists': True}},
                                          {'extra.item': {'$exists': True}}
                                          ]}]}

    not_item_entry_query = {'$or': [{'resource': {'$nin': item_resources}}, {'extra': {'$exists': False}},
                                    {'$and': [{'extra': {'$exists': True}},
                                              {'extra.guid': {'$exists': False}},
                                              {'extra._id': {'$exists': False}},
                                              {'extra.item_id': {'$exists': False}},
                                              {'extra.item': {'$exists': False}}
                                              ]}]}

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
        self.purge_old_entries()
        self.purge_orphaned_item_audits()
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

    def _extract_item_id(self, item):
        """
        Given an audit item try to extract the id of the item that it relates to
        :param item:
        :return:
        """
        try:
            if 'guid' in item['extra']:
                return item['extra']['guid']
            elif '_id' in item['extra']:
                return item['extra']['_id']
            elif 'item_id' in item['extra']:
                return item['extra']['item_id']
            elif 'item' in item['extra']:
                return item['extra']['item']
        except:
            return None
        return None

    def purge_orphaned_item_audits(self):
        """
        Purge the audit items that do not have associated entries existing in archive
        :return:
        """
        service = superdesk.get_resource_service('audit')
        current_id = None

        # Scan the audit collection for items to delete
        while True:
            query = deepcopy(self.item_entry_query)
            query['$and'].append({'_updated': {'$lte': date_to_str(self.expiry)}})
            if current_id:
                query['$and'].append({'_id': {'$gt': current_id}})
            req = ParsedRequest()
            req.sort = '[("_id", 1)]'
            req.projection = '{"_id": 1, "extra.guid": 1, "extra._id": 1, "extra.item_id": 1, "extra.item": 1}'
            req.max_results = 1000
            audits = service.get_from_mongo(req=req, lookup=query)
            if audits.count() == 0:
                break
            items = list([(item['_id'], self._extract_item_id(item)) for item in audits])
            current_id = items[len(items) - 1][0]

            batch_ids = set([i[1] for i in items])
            archive_ids = self._get_archive_ids(batch_ids)
            ids = (batch_ids - archive_ids)
            audit_ids = [i[0] for i in items if i[1] in ids]
            service.delete({'_id': {'$in': audit_ids}})

    def purge_old_entries(self):
        """
        Purge entries older than the expiry that are not related to archive items
        :return:
        """
        service = superdesk.get_resource_service('audit')
        current_date = None

        while True:
            lookup = {'$and': [self.not_item_entry_query, {'_updated': {'$lte': date_to_str(self.expiry)}}]}
            if current_date:
                lookup['$and'].append({'_updated': {'$gte': current_date}})
            req = ParsedRequest()
            req.sort = '[("_updated", 1)]'
            req.projection = '{"_id": 1, "_updated": 1}'
            req.max_results = 1000
            audits = service.get_from_mongo(req=req, lookup=lookup)
            if audits.count() == 0:
                break
            items = list([(item['_id'], item['_updated']) for item in audits])
            current_date = items[len(items) - 1][1]
            service.delete({'_id': {'$in': [i[0] for i in items]}})


superdesk.command('audit:purge', PurgeAudit())
