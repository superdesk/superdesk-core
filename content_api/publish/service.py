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

from copy import copy
from eve.utils import config, ParsedRequest

from superdesk.utc import utcnow
from superdesk.services import BaseService
from superdesk.publish.formatters.ninjs_newsroom_formatter import NewsroomNinjsFormatter
from superdesk import get_resource_service
from superdesk.metadata.item import ASSOCIATIONS, remove_metadata_for_publish
from apps.publish.enqueue.enqueue_service import EnqueueService

logger = logging.getLogger('superdesk')


class PublishService(BaseService):
    """A service for publishing to the content api.

    Serves mainly as a proxy to the data layer.
    """

    formatter = NewsroomNinjsFormatter()
    subscriber = {'config': {}}

    def publish(self, item, subscribers=None):
        """Publish an item to content api.

        This must be enabled via ``PUBLISH_TO_CONTENT_API`` setting.

        :param item: item to publish
        """

        if subscribers is None:
            subscribers = []

        if not self._filter_item(item):
            item = EnqueueService.filter_document(item)
            item = remove_metadata_for_publish(item)
            doc = self.formatter._transform_to_ninjs(item, self.subscriber)
            now = utcnow()
            doc.setdefault('firstcreated', now)
            doc.setdefault('versioncreated', now)
            doc.setdefault(config.VERSION, item.get(config.VERSION, 1))
            for _, assoc in doc.get(ASSOCIATIONS, {}).items():
                if assoc:
                    assoc.setdefault('subscribers', [str(subscriber[config.ID_FIELD]) for subscriber in subscribers])
            doc['subscribers'] = [str(sub['_id']) for sub in subscribers]
            if 'evolvedfrom' in doc:
                parent_item = self.find_one(req=None, _id=doc['evolvedfrom'])
                if parent_item:
                    doc['ancestors'] = copy(parent_item.get('ancestors', []))
                    doc['ancestors'].append(doc['evolvedfrom'])
                    doc['bookmarks'] = parent_item.get('bookmarks', [])
                else:
                    logger.warning("Failed to find evolvedfrom item '{}' for '{}'".format(
                        doc['evolvedfrom'], doc['guid'])
                    )

            self._assign_associations(item, doc)
            logger.info('publishing %s to %s' % (doc['guid'], subscribers))
            _id = self._create_doc(doc)
            if 'evolvedfrom' in doc and parent_item:
                self.system_update(parent_item['_id'], {'nextversion': _id}, parent_item)
            return _id
        else:
            return None

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            ids.append(self._create_doc(doc, **kwargs))
        return ids

    def _create_doc(self, doc, **kwargs):
        """Create a new item or update existing."""
        item = copy(doc)
        item.setdefault('_id', item.get('guid'))
        _id = item[config.ID_FIELD] = item.pop('guid')

        # merging the existing and new subscribers
        original = self.find_one(req=None, _id=_id)
        if original:
            item['subscribers'] = list(set(original.get('subscribers', [])) | set(item.get('subscribers', [])))

        self._process_associations(item, original)
        self._create_version_doc(item)
        if original:
            self.update(_id, item, original)
            return _id
        else:
            return super().create([item], **kwargs)[0]

    def _create_version_doc(self, item):
        """
        Store the item in the item version collection
        :param item:
        :return:
        """
        version_item = copy(item)
        version_item['_id_document'] = version_item.pop('_id')
        get_resource_service('items_versions').create([version_item])
        # if the update is a cancel we need to cancel all versions
        if item.get('pubstatus', '') == 'canceled':
            self._cancel_versions(item.get('_id'))

    def _cancel_versions(self, doc_id):
        """
        Given an id of a document set the pubstatus to canceled for all versions
        :param doc_id:
        :return:
        """
        query = {'_id_document': doc_id}
        update = {'pubstatus': 'canceled'}
        for item in get_resource_service('items_versions').get_from_mongo(req=None, lookup=query):
            if item.get('pubstatus') != 'canceled':
                get_resource_service('items_versions').update(item['_id'], update, item)

    def _filter_item(self, item):
        """
        Filter the item out if it matches any API Block filter conditions
        :param item:
        :return: True of the item is blocked, False if it is OK to publish it on the API.
        """
        # Get the API blocking Filters
        req = ParsedRequest()
        filter_conditions = list(get_resource_service('content_filters').get(req=req, lookup={'api_block': True}))

        # No API blocking filters
        if not filter_conditions:
            return False

        filter_service = get_resource_service('content_filters')
        for fc in filter_conditions:
            if filter_service.does_match(fc, item):
                logger.info('API Filter block {} matched for item {}.'.format(fc, item.get(config.ID_FIELD)))
                return True

        return False

    def _assign_associations(self, item, doc):
        """Assign Associations to published item

        :param dict item: item being published
        :param dit doc: ninjs documents
        """
        for assoc, assoc_item in (item.get('associations') or {}).items():
            if not assoc_item:
                continue
            doc.get('associations', {}).get(assoc)['subscribers'] = list(map(str, assoc_item.get('subscribers') or []))

    def _process_associations(self, updates, original):
        """Update associations using existing published item and ensure that associated item subscribers
        are equal or subset of the parent subscribers.
        :param updates:
        :param original:
        :return:
        """
        subscribers = updates.get('subscribers') or []
        for assoc, update_assoc in (updates.get('associations') or {}).items():
            if not update_assoc:
                continue

            if original:
                original_assoc = (original.get('associations') or {}).get(assoc)

                if original_assoc and original_assoc.get(config.ID_FIELD) == update_assoc.get(config.ID_FIELD):
                    update_assoc['subscribers'] = list(set(original_assoc.get('subscribers') or []) |
                                                       set(update_assoc.get('subscribers') or []))

            update_assoc['subscribers'] = list(set(update_assoc['subscribers']) & set(subscribers))
