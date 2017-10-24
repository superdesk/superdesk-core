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
import json

from bson.objectid import ObjectId

import superdesk
from copy import deepcopy
from flask import current_app as app
from eve.utils import ParsedRequest
from eve.versioning import versioned_id_field
from superdesk.celery_app import celery
from superdesk import get_resource_service, config
from superdesk.celery_task_utils import get_lock_id
from .resource import LEGAL_ARCHIVE_NAME, LEGAL_ARCHIVE_VERSIONS_NAME, LEGAL_PUBLISH_QUEUE_NAME, \
    LEGAL_ARCHIVE_HISTORY_NAME
from superdesk.users.services import get_display_name
from apps.archive.common import ARCHIVE
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE
from superdesk.lock import lock, unlock
from superdesk.publish.publish_queue import QueueState
from superdesk.errors import update_notifiers
from superdesk.activity import ACTIVITY_ERROR
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


def is_legal_archive_enabled():
    """Test if legal archive is enabled."""
    return app.config['LEGAL_ARCHIVE']


class LegalArchiveImport:
    log_msg_format = "{{'_id': {_id}, 'unique_name': {unique_name}, 'version': {_current_version}, " \
                     "'expired_on': {expiry}}}."

    def upsert_into_legal_archive(self, item_id):
        """Once publish actions are performed on the article do the below:

            1.  Get legal archive article.
            2.  De-normalize the expired article
            3.  Upserting Legal Archive.
            4.  Get Version History and De-normalize and Inserting Legal Archive Versions
            5.  Get History and de-normalize and insert into Legal Archive History

        :param dict item_id: id of the document from 'archive' collection.
        """
        try:

            logger.info('Import item into legal {}.'.format(item_id))

            doc = get_resource_service(ARCHIVE).find_one(req=None, _id=item_id)

            if not doc:
                logger.error('Could not find the document {} to import to legal archive.'.format(item_id))
                return

            # setting default values in case they are missing other log message will fail.
            doc.setdefault('unique_name', 'NO UNIQUE NAME')
            doc.setdefault(config.VERSION, 1)
            doc.setdefault('expiry', utcnow())

            if not doc.get(ITEM_STATE) in {CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED}:
                # at times we have seen that item is published but the item is different in the archive collection
                # this will notify admins about the issue but proceed to move the item into legal archive.
                msg = 'Invalid state: {}. Moving the item to legal archive. item: {}'.\
                    format(doc.get(ITEM_STATE), self.log_msg_format.format(**doc))
                logger.error(msg)
                update_notifiers(ACTIVITY_ERROR, msg=msg, resource=ARCHIVE)

            # required for behave test.
            legal_archive_doc = deepcopy(doc)
            legal_archive_service = get_resource_service(LEGAL_ARCHIVE_NAME)
            legal_archive_versions_service = get_resource_service(LEGAL_ARCHIVE_VERSIONS_NAME)
            legal_archive_history_service = get_resource_service(LEGAL_ARCHIVE_HISTORY_NAME)

            log_msg = self.log_msg_format.format(**legal_archive_doc)
            version_id_field = versioned_id_field(app.config['DOMAIN'][ARCHIVE])
            logger.info('Preparing Article to be inserted into Legal Archive ' + log_msg)

            # Removing irrelevant properties
            legal_archive_doc.pop(config.ETAG, None)
            legal_archive_doc.pop('lock_user', None)
            legal_archive_doc.pop('lock_session', None)
            legal_archive_doc.pop('lock_time', None)
            legal_archive_doc.pop('lock_action', None)

            logger.info('Removed irrelevant properties from the article {}'.format(log_msg))

            # Step 1
            article_in_legal_archive = legal_archive_service.find_one(req=None, _id=legal_archive_doc[config.ID_FIELD])

            if article_in_legal_archive and \
               article_in_legal_archive.get(config.VERSION, 0) > legal_archive_doc.get(config.VERSION):
                logger.info('Item {} version: {} already in legal archive. Legal Archive document version {}'.format(
                    legal_archive_doc.get(config.ID_FIELD), legal_archive_doc.get(config.VERSION),
                    article_in_legal_archive.get(config.VERSION)
                ))
                self._set_moved_to_legal(doc)
                return

            # Step 2 - De-normalizing the legal archive doc
            self._denormalize_user_desk(legal_archive_doc, log_msg)
            logger.info('De-normalized article {}'.format(log_msg))

            # Step 3 - Upserting Legal Archive
            logger.info('Upserting Legal Archive Repo with article {}'.format(log_msg))

            if article_in_legal_archive:
                legal_archive_service.put(legal_archive_doc[config.ID_FIELD], legal_archive_doc)
            else:
                legal_archive_service.post([legal_archive_doc])

            # Step 4 - Get Versions and De-normalize and Inserting Legal Archive Versions
            lookup = {version_id_field: legal_archive_doc[config.ID_FIELD]}
            versions = list(get_resource_service('archive_versions').get(req=None, lookup=lookup))
            legal_versions = list(legal_archive_versions_service.get(req=None, lookup=lookup))

            logger.info('Fetched version history for article {}'.format(log_msg))
            versions_to_insert = [version for version in versions
                                  if not any(legal_version for legal_version in legal_versions
                                             if version[config.VERSION] == legal_version[config.VERSION])]

            # Step 5 - Get History and de-normalize and insert into Legal Archive History
            lookup = {'item_id': legal_archive_doc[config.ID_FIELD]}
            history_items = list(get_resource_service('archive_history').get(req=None, lookup=lookup))
            legal_history_items = list(legal_archive_history_service.get(req=None, lookup=lookup))

            logger.info('Fetched history for article {}'.format(log_msg))
            history_to_insert = [history for history in history_items
                                 if not any(legal_version for legal_version in legal_history_items
                                            if history[config.ID_FIELD] == legal_version[config.ID_FIELD])]

            # This happens when user kills an article from Dusty Archive
            if article_in_legal_archive and \
               article_in_legal_archive[config.VERSION] < legal_archive_doc[config.VERSION] and \
               len(versions_to_insert) == 0:

                resource_def = app.config['DOMAIN'][ARCHIVE]
                versioned_doc = deepcopy(legal_archive_doc)
                versioned_doc[versioned_id_field(resource_def)] = legal_archive_doc[config.ID_FIELD]
                versioned_doc[config.ID_FIELD] = ObjectId()
                versions_to_insert.append(versioned_doc)

            for version_doc in versions_to_insert:
                self._denormalize_user_desk(version_doc,
                                            self.log_msg_format.format(_id=version_doc[version_id_field],
                                                                       unique_name=version_doc.get('unique_name'),
                                                                       _current_version=version_doc[config.VERSION],
                                                                       expiry=version_doc.get('expiry')))
                version_doc.pop(config.ETAG, None)

            if versions_to_insert:
                legal_archive_versions_service.post(versions_to_insert)
                logger.info('Inserted de-normalized versions for article {}'.format(log_msg))

            for history_doc in history_to_insert:
                self._denormalize_history(history_doc)
                history_doc.pop(config.ETAG, None)

            if history_to_insert:
                legal_archive_history_service.post(history_to_insert)
                logger.info('Inserted de-normalized history for article {}'.format(log_msg))

            # Set the flag that item is moved to legal.
            self._set_moved_to_legal(doc)

            logger.info('Upsert completed for article ' + log_msg)
        except Exception:
            logger.exception('Failed to import into legal archive {}.'.format(item_id))
            raise

    def _denormalize_history(self, history_item):
        """
        De-normalizes history items
        """
        msg = "item_id: {} and version: {}".format(history_item['item_id'], history_item['version'])

        # De-normalizing User Details
        history_item['user_id'] = self.__get_user_name(history_item.get('user_id'))

        # De-normalizing Desk and Stage details
        history_update = history_item.get('update')
        if history_update:
            if history_update.get('task') and history_update.get('task').get('desk'):
                desk = get_resource_service('desks').find_one(req=None, _id=str(history_update['task']['desk']))
                if desk:
                    history_update['task']['desk'] = desk.get('name')
                    logger.info('De-normalized Desk Details for article history {}'.format(msg))
                else:
                    logger.info('Desk Details Not Found: {}. {}'.format(history_update['task'].get('desk'), msg))

            if history_update.get('task') and history_update['task'].get('stage'):
                stage = get_resource_service('stages').find_one(req=None, _id=str(history_update['task']['stage']))
                if stage:
                    history_update['task']['stage'] = stage.get('name')
                    logger.info('De-normalized Stage Details for article {}'.format(msg))
                else:
                    logger.info('Stage Details Not Found: {}. {}'.format(history_update['task'].get('stage'),
                                                                         msg))

            if history_update.get('task') and history_update['task'].get('user'):
                    history_update['task']['user'] = self.__get_user_name(history_update['task'].get('user'))

            history_item['update'] = history_update

    def _denormalize_user_desk(self, legal_archive_doc, log_msg):
        """
        De-normalizes user, desk and stage details in legal_archive_doc.
        """

        # De-normalizing User Details
        legal_archive_doc['original_creator'] = self.__get_user_name(legal_archive_doc.get('original_creator'))
        legal_archive_doc['version_creator'] = self.__get_user_name(legal_archive_doc.get('version_creator'))

        logger.info('De-normalized User Details for article {}'.format(log_msg))

        # De-normalizing Desk and Stage details
        if legal_archive_doc.get('task'):
            if legal_archive_doc['task'].get('desk'):
                desk = get_resource_service('desks').find_one(req=None, _id=str(legal_archive_doc['task']['desk']))
                if desk:
                    legal_archive_doc['task']['desk'] = desk.get('name')
                    logger.info('De-normalized Desk Details for article {}'.format(log_msg))
                else:
                    logger.info('Desk Details Not Found: {}. {}'.format(legal_archive_doc['task'].get('desk'), log_msg))

            if legal_archive_doc['task'].get('stage'):
                stage = get_resource_service('stages').find_one(req=None, _id=str(legal_archive_doc['task']['stage']))
                if stage:
                    legal_archive_doc['task']['stage'] = stage.get('name')
                    logger.info('De-normalized Stage Details for article {}'.format(log_msg))
                else:
                    logger.info('Stage Details Not Found: {}. {}'.format(legal_archive_doc['task'].get('stage'),
                                                                         log_msg))

            legal_archive_doc['task']['user'] = self.__get_user_name(legal_archive_doc['task'].get('user'))

    def __get_user_name(self, user_id):
        """
        Retrieves display_name of the user identified by user_id
        """
        logger.info('Get User Details for ID:{}'.format(user_id))

        if not user_id:
            return ''

        user = get_resource_service('users').find_one(req=None, _id=user_id)

        if not user:
            return ''

        return get_display_name(user)

    def _set_moved_to_legal(self, doc):
        """Set the moved to legal flag.

        :param dict doc: document
        """
        get_resource_service('published').set_moved_to_legal(doc.get(config.ID_FIELD),
                                                             doc.get(config.VERSION),
                                                             True)

    def import_legal_publish_queue(self, force_move=False, page_size=500):
        """Import legal publish queue.

        :param bool force_move: True force move to legal as else false.
        :param int page_size: page_size.
        """
        logger.info('Starting to import publish queue items...')

        for items in self.get_publish_queue_items(page_size):
            if len(items):
                try:
                    self.process_queue_items(items, force_move)
                    logger.info('Imported publish queue items {} into legal publish queue.'.format(len(items)))
                except Exception:
                    logger.exception('Failed to import into legal publish queue via command')

        logger.info('Completed importing of publish queue items.')

    def process_queue_items(self, queue_items, force_move=False):
        """Process queue items.

        :param list queue_items: list of queue item to be
        :param bool force_move:
        """
        logger.info('Items to import {}.'.format(len(queue_items)))
        logger.info('Get subscribers info for de-normalising queue items.')
        subscriber_ids = list({str(queue_item['subscriber_id']) for queue_item in queue_items})
        query = {'$and': [{config.ID_FIELD: {'$in': subscriber_ids}}]}
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))
        subscribers = {str(subscriber[config.ID_FIELD]): subscriber for subscriber in subscribers}

        for queue_item in queue_items:
            try:
                self._upsert_into_legal_archive_publish_queue(queue_item, subscribers, force_move)
            except Exception:
                logger.exception("Failed to import publish queue item. {}".format(queue_item.get(config.ID_FIELD)))

    def _upsert_into_legal_archive_publish_queue(self, queue_item, subscribers, force_move):
        """Upsert into legal publish queue.

        :param dict queue_item: publish_queue collection item
        :param dict subscribers: subscribers information
        :param bool force_move: true set the flag to move to legal.
        """
        legal_publish_queue_service = get_resource_service(LEGAL_PUBLISH_QUEUE_NAME)
        legal_queue_item = deepcopy(queue_item)
        lookup = {
            'item_id': legal_queue_item.get('item_id'),
            'item_version': legal_queue_item.get('item_version'),
            'subscriber_id': legal_queue_item.get('subscriber_id')
        }

        log_msg = '{item_id} -- version {item_version} -- subscriber {subscriber_id}.'.format(**lookup)

        logger.info('Processing queue item: {}'.format(log_msg))

        existing_queue_item = legal_publish_queue_service.find_one(req=None, _id=legal_queue_item.get(config.ID_FIELD))
        if str(queue_item['subscriber_id']) in subscribers:
            legal_queue_item['subscriber_id'] = subscribers[str(queue_item['subscriber_id'])]['name']
            legal_queue_item['_subscriber_id'] = queue_item['subscriber_id']
        else:
            logger.warn('Subscriber is deleted from the system: {}'.format(log_msg))
            legal_queue_item['subscriber_id'] = 'Deleted Subscriber'
            legal_queue_item['_subscriber_id'] = queue_item['subscriber_id']

        if not existing_queue_item:
            legal_publish_queue_service.post([legal_queue_item])
            logger.info('Inserted queue item: {}'.format(log_msg))
        else:
            legal_publish_queue_service.put(existing_queue_item.get(config.ID_FIELD), legal_queue_item)
            logger.info('Updated queue item: {}'.format(log_msg))

        if queue_item['state'] in {QueueState.SUCCESS.value,
                                   QueueState.CANCELED.value,
                                   QueueState.FAILED.value} or force_move:
            updates = dict()
            updates['moved_to_legal'] = True

            try:
                get_resource_service('publish_queue').system_update(queue_item.get(config.ID_FIELD),
                                                                    updates, queue_item)
                logger.info('Queue item moved to legal. {}'.format(log_msg))
            except Exception:
                logger.exception('Failed to set moved to legal flag for queue item {}.'.format(log_msg))

        logger.info('Processed queue item: {}'.format(log_msg))

    def get_publish_queue_items(self, page_size, expired_items=[]):
        """Get publish queue items that are not moved to legal

        :param int page_size: batch size
        :param list expired_items:
        :return list: publish queue items
        """
        query = {
            'moved_to_legal': False
        }

        if expired_items:
            query['item_id'] = {'$in': expired_items}
        else:
            query['state'] = {'$in': [QueueState.SUCCESS.value, QueueState.CANCELED.value, QueueState.FAILED.value]}

        service = get_resource_service('publish_queue')
        req = ParsedRequest()
        req.sort = '[("_id", 1)]'
        req.where = json.dumps(query)
        cursor = service.get(req=req, lookup=None)
        count = cursor.count()
        no_of_pages = 0
        if count:
            no_of_pages = len(range(0, count, page_size))
            queue_id = cursor[0][config.ID_FIELD]
        logger.info('Number of items to move to legal archive publish queue: {}, pages={}'.format(count, no_of_pages))

        for page in range(0, no_of_pages):
            logger.info('Fetching publish queue items '
                        'for page number: {}. queue_id: {}'. format((page + 1), queue_id))
            req = ParsedRequest()
            req.sort = '[("_id", 1)]'
            query['_id'] = {'$gte': str(queue_id)}
            req.where = json.dumps(query)
            req.max_results = page_size
            cursor = service.get(req=req, lookup=None)
            items = list(cursor)
            if len(items) > 0:
                queue_id = items[len(items) - 1][config.ID_FIELD]
            logger.info('Fetched No. of Items: {} for page: {} '
                        'For import in to legal archive publish_queue.'.format(len(items), (page + 1)))
            yield items


@celery.task(bind=True, default_retry_delay=180)
def import_into_legal_archive(self, item_id):
    """Called async to import into legal archive.

    :param self: celery task
    :param str item_id: document id to import into legal_archive
    """
    if not is_legal_archive_enabled():
        return
    try:
        LegalArchiveImport().upsert_into_legal_archive(item_id)
    except Exception:
        # we can't loose stuff for legal archive.
        logger.exception('Failed to process legal archive doc {}. Retrying again.'.format(item_id))
        raise self.retry()


class ImportLegalPublishQueueCommand(superdesk.Command):
    """
    This command import publish queue records into legal publish queue.
    """

    default_page_size = 500

    option_list = [
        superdesk.Option('--page-size', '-p', dest='page_size', required=False)
    ]

    def run(self, page_size=None):
        if not is_legal_archive_enabled():
            return
        logger.info('Import to Legal Publish Queue')
        lock_name = get_lock_id('legal_archive', 'import_legal_publish_queue')
        page_size = int(page_size) if page_size else self.default_page_size
        if not lock(lock_name, expire=310):
            return
        try:
            LegalArchiveImport().import_legal_publish_queue(page_size=page_size)
        finally:
            unlock(lock_name)


class ImportLegalArchiveCommand(superdesk.Command):
    """This command import archive into legal archive.

    As per the publishing logic the import to legal archive is done asynchronously. If this fails
    then you are missing records in legal archive. Use this command to manually import archive
    items into legal archive.
    """

    default_page_size = 500

    option_list = [
        superdesk.Option('--page-size', '-p', dest='page_size', required=False)
    ]

    def run(self, page_size=None):
        if not is_legal_archive_enabled():
            return
        logger.info('Import to Legal Archive')
        lock_name = get_lock_id('legal_archive', 'import_to_legal_archive')
        page_size = int(page_size) if page_size else self.default_page_size
        if not lock(lock_name, expire=1810):
            return
        try:
            legal_archive_import = LegalArchiveImport()
            # publish_queue = get_resource_service('publish_queue')
            # move the publish item to legal archive.
            expired_items = set()
            for items in self.get_expired_items(page_size):
                for item in items:
                    self._move_to_legal(item.get('item_id'), item.get(config.VERSION), expired_items)

            # get the invalid items from archive.
            for items in get_resource_service(ARCHIVE).get_expired_items(utcnow(), invalid_only=True):
                for item in items:
                    self._move_to_legal(item.get(config.ID_FIELD), item.get(config.VERSION), expired_items)

            # if publish item is moved but publish_queue item is not.
            if len(expired_items):
                try:
                    for items in legal_archive_import.get_publish_queue_items(page_size, list(expired_items)):
                        legal_archive_import.process_queue_items(items, True)
                except Exception:
                    logger.exception('Failed to import into legal publish queue via command')

            # reset the expiry status
            archive_service = get_resource_service(ARCHIVE)
            for item_id in expired_items:
                try:
                    item = archive_service.find_one(req=None, _id=item_id)
                    if item:
                        archive_service.system_update(item_id, {'expiry_status': ''}, item)
                except Exception:
                    logger.exception('Failed to reset expiry status for item id: {}.'.format(item_id))
        except Exception:
            logger.exception('Failed to import into legal archive.')
        finally:
            unlock(lock_name)

    def _move_to_legal(self, item_id, item_version, expired_items):
        try:
            legal_archive_import = LegalArchiveImport()
            legal_archive_import.upsert_into_legal_archive(item_id)
            # set the flag to be set to true.
            get_resource_service('published').set_moved_to_legal(item_id,
                                                                 item_version, True)
            expired_items.add(item_id)
        except Exception:
            logger.exception('Failed to import into legal archive via command {}.'.format(item_id))

    def get_expired_items(self, page_size):
        """Get expired item that are not moved to legal

        :return:
        """
        query = {
            'query': {
                'filtered': {
                    'filter': {
                        'and': [
                            {'range': {'expiry': {'lt': 'now'}}},
                            {'term': {'moved_to_legal': False}},
                            {'not': {'term': {'state': CONTENT_STATE.SCHEDULED}}}
                        ]
                    }
                }
            }
        }

        service = get_resource_service('published')
        req = ParsedRequest()
        req.args = {'source': json.dumps(query)}
        req.sort = '[("publish_sequence_no", 1)]'
        cursor = service.get(req=req, lookup=None)
        count = cursor.count()
        no_of_pages = 0
        if count:
            no_of_pages = len(range(0, count, page_size))
            sequence_no = cursor[0]['publish_sequence_no']
        logger.info('Number of items to move to legal archive: {}, pages={}'.format(count, no_of_pages))

        for page in range(0, no_of_pages):
            logger.info('Fetching published items '
                        'for page number: {} sequence no: {}'. format((page + 1), sequence_no))
            req = ParsedRequest()
            page_query = deepcopy(query)
            sequence_filter = {'range': {'publish_sequence_no': {'gte': sequence_no}}}
            if page == 0:
                sequence_filter = {'range': {'publish_sequence_no': {'gte': sequence_no}}}
            else:
                sequence_filter = {'range': {'publish_sequence_no': {'gt': sequence_no}}}

            page_query['query']['filtered']['filter']['and'].append(sequence_filter)

            req.args = {'source': json.dumps(page_query)}
            req.sort = '[("publish_sequence_no", 1)]'
            req.max_results = page_size
            cursor = service.get(req=req, lookup=None)
            items = list(cursor)
            if len(items):
                sequence_no = items[len(items) - 1]['publish_sequence_no']

            logger.info('Fetched No. of Items: {} for page: {} '
                        'For import into legal archive.'.format(len(items), (page + 1)))
            yield items
