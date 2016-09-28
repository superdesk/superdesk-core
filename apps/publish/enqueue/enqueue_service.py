# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from functools import partial
import logging
import io
import json

from bson import ObjectId

from flask import current_app as app
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, SuperdeskPublishError
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, ITEM_STATE, PUBLISH_SCHEDULE
from superdesk.metadata.packages import SEQUENCE, PACKAGE_TYPE, GROUPS,\
    ROOT_GROUP, GROUP_ID, REFS, RESIDREF
from superdesk.notification import push_notification
from superdesk.publish import SUBSCRIBER_TYPES
from apps.publish.content.common import BasePublishService
from superdesk.publish.formatters import get_formatter
from copy import deepcopy
from eve.utils import config, ParsedRequest
from apps.archive.common import get_user, get_utc_schedule
from apps.packages import TakesPackageService
from apps.packages.package_service import PackageService
from apps.publish.published_item import PUBLISH_STATE, QUEUE_STATE
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE

logger = logging.getLogger(__name__)


class EnqueueService:
    """
    Creates the corresponding entries in the publish queue for items marked for publishing
    """

    publish_type = 'publish'
    published_state = 'published'

    non_digital = partial(filter, lambda s: s.get('subscriber_type', '') == SUBSCRIBER_TYPES.WIRE)
    digital = partial(filter, lambda s: (s.get('subscriber_type', '') in {SUBSCRIBER_TYPES.DIGITAL,
                                                                          SUBSCRIBER_TYPES.ALL}))
    takes_package_service = TakesPackageService()
    package_service = PackageService()

    def _enqueue_item(self, item):
        if item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and item.get(PACKAGE_TYPE):
            return self.publish(doc=item, target_media_type=SUBSCRIBER_TYPES.DIGITAL)
        elif item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and app.config.get('NO_TAKES'):
            queued = self._publish_package_items(item)
            if not queued:  # this was only published to subscribers with config.packaged on
                return self.publish(doc=item, target_media_type=SUBSCRIBER_TYPES.DIGITAL)
            else:
                return queued
        elif item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            return self._publish_package_items(item)
        elif item[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            return self.publish(item, SUBSCRIBER_TYPES.DIGITAL)
        else:
            return self.publish(item, SUBSCRIBER_TYPES.WIRE if item.get('is_take_item') else None)

    def _publish_package_items(self, package):
        """Publishes all items of a package recursively then publishes the package itself

        :param package: package to publish
        :param updates: payload
        """
        items = self.package_service.get_residrefs(package)
        subscriber_items = {}
        queued = False
        removed_items = []
        if self.publish_type in ['correct', 'kill']:
            removed_items, added_items = self._get_changed_items(items, package)
            # we raise error if correction is done on a empty package. Kill is fine.
            if len(removed_items) == len(items) and len(added_items) == 0 and self.publish_type == 'correct':
                raise SuperdeskApiError.badRequestError("Corrected package cannot be empty!")
            items.extend(added_items)

        if items:
            archive_service = get_resource_service('archive')
            for guid in items:
                package_item = archive_service.find_one(req=None, _id=guid)

                if not package_item:
                    raise SuperdeskApiError.badRequestError(
                        "Package item with id: {} has not been published.".format(guid))

                subscribers, subscriber_codes = self._get_subscribers_for_package_item(package_item)
                digital_item_id = BasePublishService().get_digital_id_for_package_item(package_item)
                self._extend_subscriber_items(subscriber_items,
                                              subscribers,
                                              package_item,
                                              digital_item_id,
                                              subscriber_codes)

            for removed_id in removed_items:
                package_item = archive_service.find_one(req=None, _id=removed_id)
                subscribers, subscriber_codes = self._get_subscribers_for_package_item(package_item)
                digital_item_id = None
                self._extend_subscriber_items(subscriber_items,
                                              subscribers,
                                              package_item,
                                              digital_item_id,
                                              subscriber_codes)

            queued = self.publish_package(package, target_subscribers=subscriber_items)

        return queued

    def _get_changed_items(self, existing_items, package):
        """Returns the added and removed items from existing_items

        :param existing_items: Existing list
        :param updates: Changes
        :return: list of removed items and list of added items
        """
        published_service = get_resource_service('published')
        req = ParsedRequest()
        query = {'query': {'filtered': {'filter': {'and': [{'term': {QUEUE_STATE: PUBLISH_STATE.QUEUED}},
                                                           {'term': {'item_id': package['item_id']}}]}}},
                 'sort': [{'publish_sequence_no': 'desc'}]}
        req.args = {'source': json.dumps(query)}
        req.max_results = 1000
        previously_published_packages = published_service.get(req=req, lookup=None)
        previously_published_package = previously_published_packages[0]

        if 'groups' in previously_published_package:
            old_items = self.package_service.get_residrefs(previously_published_package)
            added_items = list(set(existing_items) - set(old_items))
            removed_items = list(set(old_items) - set(existing_items))
            return removed_items, added_items
        else:
            return [], []

    def enqueue_item(self, item):
        """Creates the corresponding entries in the publish queue for the given item

        :return bool: True if item is queued else false.
        """
        try:
            return self._enqueue_item(item)
        except SuperdeskApiError as e:
            raise e
        except KeyError as e:
            raise SuperdeskApiError.badRequestError(
                message="Key is missing on article to be published: {}".format(str(e)))
        except Exception as e:
            logger.exception("Something bad happened while publishing %s".format(id))
            raise SuperdeskApiError.internalError(message="Failed to publish the item: {}".format(str(e)))

    def get_subscribers(self, doc, target_media_type):
        """Get subscribers for doc based on target_media_type.

        Override this method in the ArchivePublishService, ArchiveCorrectService and ArchiveKillService

        :param doc: Document to publish/correct/kill
        :param target_media_type: dictate if the doc being queued is a Takes Package or an Individual Article.
                Valid values are - Wire, Digital. If Digital then the doc being queued is a Takes Package and if Wire
                then the doc being queues is an Individual Article.
        :return: (list, list) List of filtered subscriber,
                List of subscribers that have not received item previously (empty list in this case).
        """
        raise NotImplementedError()

    def publish(self, doc, target_media_type=None):
        """Queue the content for publishing.

        1. Get the subscribers.
        2. Update the headline of wire stories with the sequence
        3. Queue the content for subscribers
        4. Queue the content for previously published subscribers if any.
        5. Sends notification if no formatter has found for any of the formats configured in Subscriber.
        6. If not queued and not formatters then raise exception.

        :param dict doc: document to publish
        :param str target_media_type: dictate if the doc being queued is a Takes Package or an Individual Article.
                Valid values are - Wire, Digital. If Digital then the doc being queued is a Takes Package and if Wire
                then the doc being queues is an Individual Article.
        :return bool: if content is queued then True else False
        :raises PublishQueueError.item_not_queued_error:
                If the nothing is queued.
        """
        # Step 1
        subscribers, subscribers_yet_to_receive, subscriber_codes = self.get_subscribers(doc, target_media_type)

        # Step 2
        if target_media_type == SUBSCRIBER_TYPES.WIRE:
            self._update_headline_sequence(doc)

        # Step 3
        no_formatters, queued = self.queue_transmission(deepcopy(doc), subscribers, subscriber_codes)

        # Step 4
        if subscribers_yet_to_receive:
            formatters_not_found, queued_new_subscribers = \
                self.queue_transmission(deepcopy(doc), subscribers_yet_to_receive, subscriber_codes)
            no_formatters.extend(formatters_not_found)
            queued = queued or queued_new_subscribers

        # Step 5
        self._push_formatter_notification(doc, no_formatters)

        # Step 6
        if not target_media_type and not queued:
            logger.exception('Nothing is saved to publish queue for story: {} for action: {}'.
                             format(doc[config.ID_FIELD], self.publish_type))

        return queued

    def _push_formatter_notification(self, doc, no_formatters=[]):
        if len(no_formatters) > 0:
            user = get_user()
            push_notification('item:publish:wrong:format',
                              item=str(doc[config.ID_FIELD]), unique_name=doc['unique_name'],
                              desk=str(doc.get('task', {}).get('desk', '')),
                              user=str(user.get(config.ID_FIELD, '')),
                              formats=no_formatters)

    def _get_subscriber_codes(self, subscribers):
        subscriber_codes = {}
        all_products = list(get_resource_service('products').get(req=None, lookup=None))

        for subscriber in subscribers:
            codes = self._get_codes(subscriber)
            products = [p for p in all_products if p[config.ID_FIELD] in subscriber.get('products', [])]

            for product in products:
                codes.extend(self._get_codes(product))
                subscriber_codes[subscriber[config.ID_FIELD]] = list(set(codes))

        return subscriber_codes

    def resend(self, doc, subscribers):
        subscriber_codes = self._get_subscriber_codes(subscribers)
        wire_subscribers = list(self.non_digital(subscribers))
        digital_subscribers = list(self.digital(subscribers))

        if len(wire_subscribers) > 0:
            doc['item_id'] = doc[config.ID_FIELD]
            self._resend_to_subscribers(doc, wire_subscribers, subscriber_codes)

        if len(digital_subscribers) > 0:
            package = self.takes_package_service.get_take_package(doc)
            package['item_id'] = package[config.ID_FIELD]
            self._resend_to_subscribers(package, digital_subscribers, subscriber_codes)

    def _resend_to_subscribers(self, doc, subscribers, subscriber_codes):
        formatter_messages, queued = self.queue_transmission(doc, subscribers, subscriber_codes)
        self._push_formatter_notification(doc, formatter_messages)
        if not queued:
            logger.exception('Nothing is saved to publish queue for story: {} for action: {}'.
                             format(doc[config.ID_FIELD], 'resend'))

    def publish_package(self, package, target_subscribers):
        """Publishes a given non-take package to given subscribers.

        For each subscriber updates the package definition with the wanted_items for that subscriber
        and removes unwanted_items that doesn't supposed to go that subscriber.
        Text stories are replaced by the digital versions.

        :param package: Package to be published
        :param target_subscribers: List of subscriber and items-per-subscriber
        """
        all_items = self.package_service.get_residrefs(package)
        no_formatters, queued = [], False
        for items in target_subscribers.values():
            updated = deepcopy(package)
            subscriber = items['subscriber']
            codes = items['codes']
            wanted_items = [item for item in items['items'] if items['items'].get(item, None)]
            unwanted_items = [item for item in all_items if item not in wanted_items]
            for i in unwanted_items:
                still_items_left = self.package_service.remove_ref_from_inmem_package(updated, i)
                if not still_items_left and self.publish_type != 'correct':
                    # if nothing left in the package to be published and
                    # if not correcting then don't send the package
                    return
            for key in wanted_items:
                self.package_service.replace_ref_in_package(updated, key, items['items'][key])

            formatters, temp_queued = self.queue_transmission(updated, [subscriber],
                                                              {subscriber[config.ID_FIELD]: codes})

            no_formatters.extend(formatters)
            if temp_queued:
                queued = temp_queued

        return queued

    def queue_transmission(self, doc, subscribers, subscriber_codes={}):
        """Method formats and then queues the article for transmission to the passed subscribers.

        ::Important Note:: Format Type across Subscribers can repeat. But we can't have formatted item generated once
        based on the format_types configured across for all the subscribers as the formatted item must have a published
        sequence number generated by Subscriber.

        :param dict doc: document to queue for transmission
        :param list subscribers: List of subscriber dict.
        :return : (list, bool) tuple of list of missing formatters and boolean flag. True if queued else False
        """
        try:
            queued = False
            no_formatters = []
            for subscriber in subscribers:
                try:
                    if doc[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED] and \
                            subscriber.get('subscriber_type', '') == SUBSCRIBER_TYPES.WIRE:
                        # wire subscribers can get only text and preformatted stories
                        continue

                    for destination in subscriber['destinations']:
                        embed_package_items = doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and \
                            PACKAGE_TYPE not in doc and destination['config'].get('packaged', False)
                        if embed_package_items:
                            doc = self._embed_package_items(doc)

                        if doc.get(PUBLISHED_IN_PACKAGE) and destination['config'].get('packaged', False) and \
                                app.config.get('NO_TAKES'):
                            continue

                        # Step 2(a)
                        formatter = get_formatter(destination['format'], doc)

                        if not formatter:  # if formatter not found then record it
                            no_formatters.append(destination['format'])
                            continue

                        formatted_docs = formatter.format(doc,
                                                          subscriber,
                                                          subscriber_codes.get(subscriber[config.ID_FIELD]))

                        for idx, publish_data in enumerate(formatted_docs):
                            if not isinstance(publish_data, dict):
                                pub_seq_num, formatted_doc = publish_data
                                formatted_docs[idx] = {'published_seq_num': pub_seq_num,
                                                       'formatted_item': formatted_doc}
                            else:
                                assert 'published_seq_num' in publish_data and 'formatted_item' in publish_data,\
                                    "missing keys in publish_data"

                        for publish_queue_item in formatted_docs:
                            publish_queue_item['item_id'] = doc['item_id']
                            publish_queue_item['item_version'] = doc[config.VERSION]
                            publish_queue_item['subscriber_id'] = subscriber[config.ID_FIELD]
                            publish_queue_item['codes'] = subscriber_codes.get(subscriber[config.ID_FIELD])
                            publish_queue_item['destination'] = destination
                            # publish_schedule is just to indicate in the queue item is create via scheduled item
                            publish_queue_item[PUBLISH_SCHEDULE] = get_utc_schedule(doc, PUBLISH_SCHEDULE) or None
                            publish_queue_item['unique_name'] = doc.get('unique_name', None)
                            publish_queue_item['content_type'] = doc.get('type', None)
                            publish_queue_item['headline'] = doc.get('headline', None)
                            publish_queue_item['publishing_action'] = self.published_state
                            publish_queue_item['ingest_provider'] = \
                                ObjectId(doc.get('ingest_provider')) if doc.get('ingest_provider') else None
                            if doc.get(PUBLISHED_IN_PACKAGE):
                                publish_queue_item[PUBLISHED_IN_PACKAGE] = doc[PUBLISHED_IN_PACKAGE]
                            try:
                                encoded_item = publish_queue_item.pop('encoded_item')
                            except KeyError:
                                pass
                            else:
                                binary = io.BytesIO(encoded_item)
                                publish_queue_item['encoded_item_id'] = app.storage.put(binary)
                            publish_queue_item.pop(ITEM_STATE, None)
                            get_resource_service('publish_queue').post([publish_queue_item])
                            queued = True
                except:
                    logger.exception("Failed to queue item for id {} with headline {} for subscriber {}."
                                     .format(doc.get(config.ID_FIELD), doc.get('headline'), subscriber.get('name')))

            return no_formatters, queued
        except:
            raise

    def _embed_package_items(self, package):
        """Embeds all package items in the package document."""
        for group in package.get(GROUPS, []):
            if group[GROUP_ID] == ROOT_GROUP:
                continue
            for ref in group[REFS]:
                if RESIDREF not in ref:
                    continue
                package_item = get_resource_service('published').find_one(req=None, item_id=ref[RESIDREF],
                                                                          _current_version=ref[config.VERSION])
                if not package_item:
                    msg = 'Can not find package %s published item %s' % (package['item_id'], ref['residRef'])
                    raise SuperdeskPublishError(500, msg)
                package_item[config.ID_FIELD] = package_item['item_id']
                ref['package_item'] = package_item
        return package

    def _update_headline_sequence(self, doc):
        """Updates the headline of the text story if there's any sequence value in it."""
        if doc.get(SEQUENCE):
            doc['headline'] = '{}={}'.format(doc['headline'], doc.get(SEQUENCE))

    def _get_subscribers_for_package_item(self, package_item):
        """Finds the list of subscribers for a given item in a packag

        :param package_item: item in a package
        :return list: List of subscribers
        :return string: Digital item id if there's one otherwise None
        """
        if package_item[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            query = {'$and': [{'item_id': package_item[config.ID_FIELD]},
                              {'publishing_action': package_item[ITEM_STATE]}]}
        else:
            package_item_takes_package = self.takes_package_service.get_take_package(package_item)
            if not package_item_takes_package:
                # this item has not been published to digital subscribers so
                # the list of subscribers are empty
                return [], {}

            query = {'$and': [{'item_id': package_item_takes_package[config.ID_FIELD]},
                              {'publishing_action': package_item_takes_package[ITEM_STATE]}]}

        return self._get_subscribers_for_previously_sent_items(query)

    def _get_subscribers_for_previously_sent_items(self, lookup):
        """Returns list of subscribers that have previously received the item.

        :param dict lookup: elastic query to filter the publish queue
        :return: list of subscribers and list of product codes per subscriber
        """
        req = ParsedRequest()
        subscribers = []
        subscriber_codes = {}
        queued_items = list(get_resource_service('publish_queue').get(req=req, lookup=lookup))
        if len(queued_items) > 0:
            subscriber_ids = {queued_item['subscriber_id'] for queued_item in queued_items}
            subscriber_codes = {q['subscriber_id']: q.get('codes', []) for q in queued_items}
            query = {'$and': [{config.ID_FIELD: {'$in': list(subscriber_ids)}}]}
            subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))
        return subscribers, subscriber_codes

    def filter_subscribers(self, doc, subscribers, target_media_type):
        """Filter subscribers to whom the current document is going to be delivered.

        :param doc: Document to publish/kill/correct
        :param subscribers: List of Subscribers that might potentially get this document
        :param target_media_type: dictate if the doc being queued is a Takes Package or an Individual Article.
                Valid values are - Wire, Digital. If Digital then the doc being queued is a Takes Package and if Wire
                then the doc being queues is an Individual Article.
        :return: List of of filtered subscribers and list of product codes per subscriber.
        """
        filtered_subscribers = []
        subscriber_codes = {}
        req = ParsedRequest()
        req.args = {'is_global': True}
        filter_service = get_resource_service('content_filters')
        existing_products = {p[config.ID_FIELD]: p for p in
                             list(get_resource_service('products').get(req=req, lookup=None))}
        global_filters = list(filter_service.get(req=req, lookup=None))

        for subscriber in subscribers:
            if target_media_type and subscriber.get('subscriber_type', '') != SUBSCRIBER_TYPES.ALL:
                can_send_takes_packages = subscriber['subscriber_type'] == SUBSCRIBER_TYPES.DIGITAL
                if target_media_type == SUBSCRIBER_TYPES.WIRE and can_send_takes_packages or \
                        target_media_type == SUBSCRIBER_TYPES.DIGITAL and not can_send_takes_packages:
                    continue

            conforms, skip_filters = self.conforms_subscriber_targets(subscriber, doc)
            if not conforms:
                continue

            if not self.conforms_global_filter(subscriber, global_filters, doc):
                continue

            product_codes = self._get_codes(subscriber)
            subscriber_added = False
            for product_id in subscriber.get('products', []):
                # check if the product filter conforms with the story
                product = existing_products.get(product_id)

                if not product:
                    continue

                if not self.conforms_product_targets(product, doc):
                    continue

                if self.conforms_content_filter(product, doc):
                    # gather the codes of products
                    product_codes.extend(self._get_codes(product))
                    if not subscriber_added:
                        filtered_subscribers.append(subscriber)
                        subscriber_added = True

            if skip_filters and not subscriber_added:
                filtered_subscribers.append(subscriber)
                subscriber_added = True

            # unify the list of codes by removing duplicates
            if subscriber_added:
                subscriber_codes[subscriber[config.ID_FIELD]] = list(set(product_codes))

        return filtered_subscribers, subscriber_codes

    def conforms_product_targets(self, product, article):
        """Check product targets.

        Checks if the given article has any target information and if it does
        it checks if the product satisfies any of the target information

        :param product: Product to test
        :param article: article
        :return:
            bool: True if the article conforms the targets for the given product
        """
        geo_restrictions = product.get('geo_restrictions')

        # If not targeted at all then Return true
        if not BasePublishService().is_targeted(article, 'target_regions'):
            return geo_restrictions is None

        if geo_restrictions:
            for region in article.get('target_regions', []):
                if region['qcode'] == geo_restrictions and region['allow']:
                    return True
                if region['qcode'] != geo_restrictions and not region['allow']:
                    return True
        return False

    def conforms_subscriber_targets(self, subscriber, article):
        """Check subscriber targets.

        Checks if the given article has any target information and if it does
        it checks if the subscriber satisfies any of the target information

        :param subscriber: Subscriber to test
        :param article: article
        :return:
            bool: True/False if the article conforms the targets
            bool: True if the given subscriber is specifically targeted, False otherwise
        """
        # If not targeted at all then Return true
        if not BasePublishService().is_targeted(article, 'target_subscribers') and \
                not BasePublishService().is_targeted(article, 'target_types'):
            return True, False

        subscriber_type = subscriber.get('subscriber_type')

        for t in article.get('target_subscribers', []):
            if str(t.get('_id')) == str(subscriber['_id']):
                return True, True

        if subscriber_type:
            for t in article.get('target_types', []):
                if t['qcode'] == subscriber_type and t['allow']:
                    return True, False
                if t['qcode'] != subscriber_type and not t['allow']:
                    return True, False

        # If there's a region target then continue with the subscriber to check products
        if BasePublishService().is_targeted(article, 'target_regions'):
            return True, False

        # Nothing matches so this subscriber doesn't conform
        return False, False

    def conforms_content_filter(self, product, doc):
        """Checks if the document matches the subscriber filter

        :param product: Product where the filter is used
        :param doc: Document to test the filter against
        :return:
        True if there's no filter
        True if matches and permitting
        False if matches and blocking
        False if doesn't match and permitting
        True if doesn't match and blocking
        """
        content_filter = product.get('content_filter')

        if content_filter is None or 'filter_id' not in content_filter or content_filter['filter_id'] is None:
            return True

        service = get_resource_service('content_filters')
        filter = service.find_one(req=None, _id=content_filter['filter_id'])
        does_match = service.does_match(filter, doc)

        if does_match:
            return content_filter['filter_type'] == 'permitting'
        else:
            return content_filter['filter_type'] == 'blocking'

    def conforms_global_filter(self, subscriber, global_filters, doc):
        """Check gloval filter

        Checks if subscriber has a override rule against each of the
        global filter and if not checks if document matches the global filter

        :param subscriber: Subscriber to get if the global filter is overriden
        :param global_filters: List of all global filters
        :param doc: Document to test the global filter against
        :return: True if at least one global filter is not overriden
        and it matches the document
        False if global filter matches the document or all of them overriden
        """
        service = get_resource_service('content_filters')
        gfs = subscriber.get('global_filters', {})
        for global_filter in global_filters:
            if gfs.get(str(global_filter[config.ID_FIELD]), True):
                # Global filter applies to this subscriber
                if service.does_match(global_filter, doc):
                    # All global filters behaves like blocking filters
                    return False
        return True

    def _extend_subscriber_items(self, subscriber_items, subscribers, item, digital_item_id, subscriber_codes):
        """Extends the subscriber_items with the given list of subscribers for the item

        :param subscriber_items: The existing list of subscribers
        :param subscribers: New subscribers that item has been published to - to be added
        :param item: item that has been published
        :param digital_item_id: digital_item_id
        """
        item_id = item[config.ID_FIELD]
        for subscriber in subscribers:
            sid = subscriber[config.ID_FIELD]
            item_list = subscriber_items.get(sid, {}).get('items', {})
            item_list[item_id] = digital_item_id
            subscriber_items[sid] = {'subscriber': subscriber,
                                     'items': item_list,
                                     'codes': subscriber_codes.get(sid, [])}

    def _get_codes(self, item):
        if item.get('codes'):
            return [c.strip() for c in item.get('codes').split(',') if c]
        else:
            return []
