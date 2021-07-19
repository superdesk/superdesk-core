# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import io
import json
import logging

from bson import ObjectId
from functools import partial
import content_api
from flask import current_app as app
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError, SuperdeskPublishError
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, ITEM_STATE, PUBLISH_SCHEDULE, ASSOCIATIONS, MEDIA_TYPES
from superdesk.metadata.packages import GROUPS, ROOT_GROUP, GROUP_ID, REFS, RESIDREF
from superdesk.notification import push_notification
from superdesk.publish import SUBSCRIBER_TYPES
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish.formatters import get_formatter
from apps.publish.content.common import BasePublishService
from copy import deepcopy
from eve.utils import config, ParsedRequest
from apps.archive.common import get_user, get_utc_schedule
from apps.packages.package_service import PackageService
from apps.publish.published_item import PUBLISH_STATE, QUEUE_STATE
from apps.content_types import apply_schema
from datetime import datetime
import pytz
from flask_babel import _

logger = logging.getLogger(__name__)


class EnqueueService:
    """
    Creates the corresponding entries in the publish queue for items marked for publishing
    """

    publish_type = "publish"
    published_state = "published"

    non_digital = partial(filter, lambda s: s.get("subscriber_type", "") == SUBSCRIBER_TYPES.WIRE)
    digital = partial(
        filter, lambda s: (s.get("subscriber_type", "") in {SUBSCRIBER_TYPES.DIGITAL, SUBSCRIBER_TYPES.ALL})
    )
    package_service = PackageService()

    filters = None

    def __init__(self, published_state=None):
        if published_state is not None:
            self.published_state = published_state

    def get_filters(self):
        """Retrieve all of the available filter conditions and content filters if they have not yet been retrieved or
        they have been updated. This avoids the filtering functions having to repeatedly retireve the individual filter
        records.

        :return:
        """

        # Get the most recent update time to the filter conditions and content_filters
        req = ParsedRequest()
        req.sort = "-_updated"
        req.max_results = 1
        mindate = datetime.min.replace(tzinfo=pytz.UTC)
        latest_fc = next(get_resource_service("filter_conditions").get_from_mongo(req=req, lookup=None), {}).get(
            "_updated", mindate
        )
        latest_cf = next(get_resource_service("content_filters").get_from_mongo(req=req, lookup=None), {}).get(
            "_updated", mindate
        )

        if (
            not self.filters
            or latest_fc > self.filters.get("latest_filter_conditions", mindate)
            or latest_fc == mindate
            or latest_cf > self.filters.get("latest_content_filters", mindate)
            or latest_cf == mindate
        ):
            logger.debug("Getting content filters and filter conditions")
            self.filters = dict()
            self.filters["filter_conditions"] = dict()
            self.filters["content_filters"] = dict()
            for fc in get_resource_service("filter_conditions").get(req=None, lookup={}):
                self.filters["filter_conditions"][fc.get("_id")] = {"fc": fc}
                self.filters["latest_filter_conditions"] = (
                    fc.get("_updated")
                    if fc.get("_updated") > self.filters.get("latest_filter_conditions", mindate)
                    else self.filters.get("latest_filter_conditions", mindate)
                )
            for cf in get_resource_service("content_filters").get(req=None, lookup={}):
                self.filters["content_filters"][cf.get("_id")] = {"cf": cf}
                self.filters["latest_content_filters"] = (
                    cf.get("_updated")
                    if cf.get("_updated") > self.filters.get("latest_content_filters", mindate)
                    else self.filters.get("latest_content_filters", mindate)
                )
        else:
            logger.debug("Using chached content filters and filters conditions")

    def _enqueue_item(self, item, content_type=None):
        item_to_queue = deepcopy(item)
        if item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            queued = self._publish_package_items(item_to_queue)
            if not queued:  # this was only published to subscribers with config.packaged on
                return self.publish(doc=item_to_queue, target_media_type=SUBSCRIBER_TYPES.DIGITAL)
            else:
                return queued
        elif content_type:
            return self.publish(item_to_queue, None, content_type)
        elif item[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            return self.publish(item_to_queue, SUBSCRIBER_TYPES.DIGITAL)
        else:
            return self.publish(item_to_queue, None)

    def _publish_package_items(self, package):
        """Publishes all items of a package recursively then publishes the package itself

        :param package: package to publish
        :param updates: payload
        """
        items = self.package_service.get_residrefs(package)
        subscriber_items = {}
        queued = False
        removed_items = []
        if self.publish_type in ["correct", "kill"]:
            removed_items, added_items = self._get_changed_items(items, package)
            # we raise error if correction is done on a empty package. Kill is fine.
            if len(removed_items) == len(items) and len(added_items) == 0 and self.publish_type == "correct":
                raise SuperdeskApiError.badRequestError(_("Corrected package cannot be empty!"))
            items.extend(added_items)

        if items:
            archive_service = get_resource_service("archive")
            for guid in items:
                package_item = archive_service.find_one(req=None, _id=guid)

                if not package_item:
                    raise SuperdeskApiError.badRequestError(
                        _("Package item with id: {guid} has not been published.").format(guid=guid)
                    )

                subscribers, subscriber_codes, associations = self._get_subscribers_for_package_item(package_item)
                package_item_id = package_item[config.ID_FIELD]
                self._extend_subscriber_items(
                    subscriber_items, subscribers, package_item, package_item_id, subscriber_codes
                )

            for removed_id in removed_items:
                package_item = archive_service.find_one(req=None, _id=removed_id)
                subscribers, subscriber_codes, associations = self._get_subscribers_for_package_item(package_item)
                package_item_id = None
                self._extend_subscriber_items(
                    subscriber_items, subscribers, package_item, package_item_id, subscriber_codes
                )

            queued = self.publish_package(package, target_subscribers=subscriber_items)

        return queued

    def _get_changed_items(self, existing_items, package):
        """Returns the added and removed items from existing_items

        :param existing_items: Existing list
        :param updates: Changes
        :return: list of removed items and list of added items
        """
        published_service = get_resource_service("published")
        req = ParsedRequest()
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"terms": {QUEUE_STATE: [PUBLISH_STATE.QUEUED, PUBLISH_STATE.QUEUED_NOT_TRANSMITTED]}},
                            {"term": {"item_id": package["item_id"]}},
                        ]
                    }
                }
            },
            "sort": [{"publish_sequence_no": "desc"}],
        }
        req.args = {"source": json.dumps(query)}
        req.max_results = 1
        previously_published_packages = published_service.get(req=req, lookup=None)

        if not previously_published_packages.count():
            return [], []

        previously_published_package = previously_published_packages[0]

        if "groups" in previously_published_package:
            old_items = self.package_service.get_residrefs(previously_published_package)
            added_items = list(set(existing_items) - set(old_items))
            removed_items = list(set(old_items) - set(existing_items))
            return removed_items, added_items
        else:
            return [], []

    def enqueue_item(self, item, content_type=None):
        """Creates the corresponding entries in the publish queue for the given item

        :param item: Item to enqueue
        :param content_type: item content type
        :return bool: True if item is queued else false.
        """
        try:
            return self._enqueue_item(item, content_type)
        except SuperdeskApiError as e:
            raise e
        except KeyError as e:
            raise SuperdeskApiError.badRequestError(
                message=_("Key is missing on article to be published: {exception}").format(exception=str(e))
            )
        except Exception as e:
            logger.exception("Something bad happened while publishing {}".format(id))
            raise SuperdeskApiError.internalError(
                message=_("Failed to publish the item: {exception}").format(exception=str(e)), exception=e
            )

    def get_subscribers(self, doc, target_media_type):
        """Get subscribers for doc based on target_media_type.

        Override this method in the ArchivePublishService, ArchiveCorrectService and ArchiveKillService

        :param doc: Document to publish/correct/kill
        :param target_media_type: Valid values are - Wire, Digital.
        :return: (list, list) List of filtered subscriber,
                List of subscribers that have not received item previously (empty list in this case).
        """
        raise NotImplementedError()

    def publish(self, doc, target_media_type=None, content_type=None):
        """Queue the content for publishing.

        1. Get the subscribers.
        2. Queue the content for subscribers
        3. Sends notification if no formatter has found for any of the formats configured in Subscriber.
        4. If not queued and not formatters then raise exception.
        5. Publish the content to content api.

        :param dict doc: document to publish
        :param str target_media_type: Valid values are - Wire, Digital.
        :param str content_type: doc content type, None for content
        :return bool: if content is queued then True else False
        :raises PublishQueueError.item_not_queued_error:
                If the nothing is queued.
        """
        sent = False

        # Step 1
        subscribers, subscriber_codes, associations = self.get_subscribers(doc, target_media_type)
        # Step 2
        no_formatters, queued = self.queue_transmission(
            deepcopy(doc), subscribers, subscriber_codes, associations, sent
        )

        # Step 3
        self._push_formatter_notification(doc, no_formatters)

        # Step 4
        if not target_media_type and not queued:
            level = logging.INFO
            if app.config["PUBLISH_NOT_QUEUED_ERROR"] and not app.config.get("SUPERDESK_TESTING"):
                level = logging.ERROR
            logger.log(
                level,
                "Nothing is saved to publish queue for story: {} for action: {}".format(
                    doc[config.ID_FIELD], self.publish_type
                ),
            )

        # Step 5
        if not content_type:
            self.publish_content_api(doc, [s for s in subscribers if s.get("api_enabled")])

        return queued

    def publish_content_api(self, doc, subscribers):
        """
        Publish item to content api
        :param dict doc: content api item
        :param list subscribers: list of subscribers
        """
        try:
            if content_api.is_enabled():
                get_resource_service("content_api").publish(doc, subscribers)
        except Exception:
            logger.exception(
                "Failed to queue item to API for item: {} for action {}".format(doc[config.ID_FIELD], self.publish_type)
            )

    def _push_formatter_notification(self, doc, no_formatters=None):
        if no_formatters is None:
            no_formatters = []

        if len(no_formatters) > 0:
            user = get_user()
            push_notification(
                "item:publish:wrong:format",
                item=str(doc[config.ID_FIELD]),
                unique_name=doc.get("unique_name"),
                desk=str(doc.get("task", {}).get("desk", "")),
                user=str(user.get(config.ID_FIELD, "")),
                formats=no_formatters,
            )

    def _get_subscriber_codes(self, subscribers):
        subscriber_codes = {}
        all_products = list(get_resource_service("products").get(req=None, lookup=None))

        for subscriber in subscribers:
            codes = self._get_codes(subscriber)
            products = [p for p in all_products if p[config.ID_FIELD] in subscriber.get("products", [])]

            for product in products:
                codes.extend(self._get_codes(product))
                subscriber_codes[subscriber[config.ID_FIELD]] = list(set(codes))

        return subscriber_codes

    def resend(self, doc, subscribers):
        """Resend doc to subscribers

        :param dict doc: doc to resend
        :param list subscribers: list of subscribers
        :return:
        """
        subscriber_codes = self._get_subscriber_codes(subscribers)
        wire_subscribers = list(self.non_digital(subscribers))
        digital_subscribers = list(self.digital(subscribers))

        for subscriber in wire_subscribers:
            subscriber["api_enabled"] = len(subscriber.get("api_products") or []) > 0

        for subscriber in digital_subscribers:
            subscriber["api_enabled"] = len(subscriber.get("api_products") or []) > 0

        doc["item_id"] = doc[config.ID_FIELD]
        associations = self._resend_associations_to_subscribers(doc, subscribers)
        if len(wire_subscribers) > 0:
            self._resend_to_subscribers(doc, wire_subscribers, subscriber_codes, associations)
            self.publish_content_api(
                doc, [subscriber for subscriber in wire_subscribers if subscriber.get("api_enabled")]
            )

        if len(digital_subscribers) > 0:
            package = None
            self._resend_to_subscribers(doc, digital_subscribers, subscriber_codes, associations)

            self.publish_content_api(
                package or doc, [subscriber for subscriber in digital_subscribers if subscriber.get("api_enabled")]
            )

    def _resend_associations_to_subscribers(self, doc, subscribers):
        """
        On resend association are also sent to the subscribers.
        :param dict doc: item to resend
        :param list subscribers: list of subscribers
        :return dict: associations
        """
        if not doc.get(ASSOCIATIONS):
            return {}

        associations = {}

        for assoc_id, item in doc.get(ASSOCIATIONS).items():
            if not item:
                continue

            item["subscribers"] = []

            for s in subscribers:
                item["subscribers"].append(s.get(config.ID_FIELD))
                if not associations.get(s.get(config.ID_FIELD)):
                    associations[s.get(config.ID_FIELD)] = []

                associations[s.get(config.ID_FIELD)].append(item.get(config.ID_FIELD))
        return associations

    def _resend_to_subscribers(self, doc, subscribers, subscriber_codes, associations=None):
        if associations is None:
            associations = {}
        formatter_messages, queued = self.queue_transmission(doc, subscribers, subscriber_codes, associations)
        self._push_formatter_notification(doc, formatter_messages)
        if not queued:
            logger.exception(
                "Nothing is saved to publish queue for story: {} for action: {}".format(doc[config.ID_FIELD], "resend")
            )

    def publish_package(self, package, target_subscribers):
        """Publishes a given package to given subscribers.

        For each subscriber updates the package definition with the wanted_items for that subscriber
        and removes unwanted_items that doesn't supposed to go that subscriber.
        Text stories are replaced by the digital versions.

        :param package: Package to be published
        :param target_subscribers: List of subscriber and items-per-subscriber
        """
        all_items = self.package_service.get_residrefs(package)
        no_formatters, queued = [], False
        subscribers = []
        for items in target_subscribers.values():
            updated = deepcopy(package)
            subscriber = items["subscriber"]
            codes = items["codes"]
            wanted_items = [item for item in items["items"] if items["items"].get(item, None)]
            unwanted_items = [item for item in all_items if item not in wanted_items]
            for i in unwanted_items:
                still_items_left = self.package_service.remove_ref_from_inmem_package(updated, i)
                if not still_items_left and self.publish_type != "correct":
                    # if nothing left in the package to be published and
                    # if not correcting then don't send the package
                    return
            for key in wanted_items:
                try:
                    self.package_service.replace_ref_in_package(updated, key, items["items"][key])
                except KeyError:
                    continue

            formatters, temp_queued = self.queue_transmission(
                updated, [subscriber], {subscriber[config.ID_FIELD]: codes}, sent=True
            )

            subscribers.append(subscriber)
            no_formatters.extend(formatters)
            if temp_queued:
                queued = temp_queued

            delivery_types = [d["delivery_type"] for d in self.get_destinations(subscriber)]
            is_content_api_delivery = "content_api" in delivery_types
            # packages for content_api will not be transmitted
            # so we need to publish them here
            if is_content_api_delivery and subscriber.get("api_enabled"):
                self.publish_content_api(package, [subscriber])

        return queued

    def get_destinations(self, subscriber):
        destinations = subscriber.get("destinations") or []
        if subscriber.get("api_enabled"):
            destinations.append({"name": "content api", "delivery_type": "content_api", "format": "ninjs"})
        return destinations

    def queue_transmission(self, doc, subscribers, subscriber_codes=None, associations=None, sent=False):
        """Method formats and then queues the article for transmission to the passed subscribers.

        ::Important Note:: Format Type across Subscribers can repeat. But we can't have formatted item generated once
        based on the format_types configured across for all the subscribers as the formatted item must have a published
        sequence number generated by Subscriber.

        :param dict doc: document to queue for transmission
        :param list subscribers: List of subscriber dict.
        :return : (list, bool) tuple of list of missing formatters and boolean flag. True if queued else False
        """
        if associations is None:
            associations = {}
        if subscriber_codes is None:
            subscriber_codes = {}

        try:
            if config.PUBLISH_ASSOCIATIONS_RESEND and not sent:
                is_correction = doc.get("state") in ["corrected", "being_corrected"]
                is_update = doc.get("rewrite_of")
                is_new = not is_correction and not is_update

                if config.PUBLISH_ASSOCIATIONS_RESEND == "new" and is_new:
                    self.resend_association_items(doc)
                elif config.PUBLISH_ASSOCIATIONS_RESEND == "corrections":
                    self.resend_association_items(doc)
                elif config.PUBLISH_ASSOCIATIONS_RESEND == "updates" and not is_correction:
                    self.resend_association_items(doc)

            queued = False
            no_formatters = []
            for subscriber in subscribers:

                try:
                    if (
                        doc[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]
                        and subscriber.get("subscriber_type", "") == SUBSCRIBER_TYPES.WIRE
                    ):
                        # wire subscribers can get only text and preformatted stories
                        continue

                    for destination in self.get_destinations(subscriber):
                        embed_package_items = doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE and (
                            destination.get("config") or {}
                        ).get("packaged", False)
                        if embed_package_items:
                            doc = self._embed_package_items(doc)

                        if doc.get(PUBLISHED_IN_PACKAGE) and (destination.get("config") or {}).get("packaged", False):
                            continue

                        # Step 2(a)
                        formatter = get_formatter(destination["format"], doc)

                        if not formatter:  # if formatter not found then record it
                            no_formatters.append(destination["format"])
                            continue

                        formatter.set_destination(destination, subscriber)
                        formatted_docs = formatter.format(
                            self.filter_document(doc), subscriber, subscriber_codes.get(subscriber[config.ID_FIELD])
                        )

                        for idx, publish_data in enumerate(formatted_docs):
                            if not isinstance(publish_data, dict):
                                pub_seq_num, formatted_doc = publish_data
                                formatted_docs[idx] = {
                                    "published_seq_num": pub_seq_num,
                                    "formatted_item": formatted_doc,
                                }
                            else:
                                assert (
                                    "published_seq_num" in publish_data and "formatted_item" in publish_data
                                ), "missing keys in publish_data"

                        for publish_queue_item in formatted_docs:
                            publish_queue_item["item_id"] = doc["item_id"]
                            publish_queue_item["item_version"] = doc[config.VERSION]
                            publish_queue_item["subscriber_id"] = subscriber[config.ID_FIELD]
                            publish_queue_item["codes"] = subscriber_codes.get(subscriber[config.ID_FIELD])
                            publish_queue_item["destination"] = destination
                            # publish_schedule is just to indicate in the queue item is create via scheduled item
                            publish_queue_item[PUBLISH_SCHEDULE] = get_utc_schedule(doc, PUBLISH_SCHEDULE) or None
                            publish_queue_item["unique_name"] = doc.get("unique_name", None)
                            publish_queue_item["content_type"] = doc.get("type", None)
                            publish_queue_item["headline"] = doc.get("headline", None)
                            publish_queue_item["publishing_action"] = self.published_state
                            publish_queue_item["ingest_provider"] = (
                                ObjectId(doc.get("ingest_provider")) if doc.get("ingest_provider") else None
                            )
                            publish_queue_item["associated_items"] = associations.get(subscriber[config.ID_FIELD], [])
                            publish_queue_item["priority"] = subscriber.get("priority")

                            if doc.get(PUBLISHED_IN_PACKAGE):
                                publish_queue_item[PUBLISHED_IN_PACKAGE] = doc[PUBLISHED_IN_PACKAGE]
                            try:
                                encoded_item = publish_queue_item.pop("encoded_item")
                            except KeyError:
                                pass
                            else:
                                binary = io.BytesIO(encoded_item)
                                publish_queue_item["encoded_item_id"] = app.storage.put(binary)
                            publish_queue_item.pop(ITEM_STATE, None)

                            # content api delivery will be marked as SUCCESS in queue
                            get_resource_service("publish_queue").post([publish_queue_item])
                            queued = True

                except Exception:
                    logger.exception(
                        "Failed to queue item for id {} with headline {} for subscriber {}.".format(
                            doc.get(config.ID_FIELD), doc.get("headline"), subscriber.get("name")
                        )
                    )

            return no_formatters, queued
        except Exception:
            raise

    def get_unique_associations(self, associated_items):
        """This method is used for the removing duplicate associate items
        :param dict associated_items: all the associate item
        """
        associations = {}
        for association in associated_items.values():
            if not association:
                continue
            item_id = association.get("_id")
            if item_id and item_id not in associations.keys():
                associations[item_id] = association
        return associations.values()

    def resend_association_items(self, doc):
        """This method is used to resend assciation items.
        :param dict doc: document
        """
        associated_items = doc.get(ASSOCIATIONS)
        if associated_items:
            for association in self.get_unique_associations(associated_items):
                # resend only media association

                if association.get("type") not in MEDIA_TYPES or association.get("is_queued"):
                    continue

                archive_article = get_resource_service("archive").find_one(req=None, _id=association.get("_id"))
                if not archive_article:
                    continue

                associated_article = get_resource_service("published").find_one(
                    req=None, item_id=archive_article["_id"], _current_version=archive_article["_current_version"]
                )
                if associated_article and associated_article.get("state") not in ["unpublished", "killed"]:
                    from apps.publish.enqueue import get_enqueue_service

                    get_enqueue_service(associated_article.get("operation")).publish(associated_article)

    def _embed_package_items(self, package):
        """Embeds all package items in the package document."""
        for group in package.get(GROUPS, []):
            if group[GROUP_ID] == ROOT_GROUP:
                continue
            for ref in group[REFS]:
                if RESIDREF not in ref:
                    continue
                package_item = get_resource_service("published").find_one(
                    req=None, item_id=ref[RESIDREF], _current_version=ref[config.VERSION]
                )
                if not package_item:
                    msg = _("Can not find package {package} published item {item}").format(
                        package=package["item_id"], item=ref["residRef"]
                    )
                    raise SuperdeskPublishError(500, msg)
                package_item[config.ID_FIELD] = package_item["item_id"]
                ref["package_item"] = package_item
        return package

    def _get_subscribers_for_package_item(self, package_item):
        """Finds the list of subscribers for a given item in a package

        :param package_item: item in a package
        :return list: List of subscribers
        """
        query = {"$and": [{"item_id": package_item[config.ID_FIELD]}, {"publishing_action": package_item[ITEM_STATE]}]}

        return self._get_subscribers_for_previously_sent_items(query)

    def _get_subscribers_for_previously_sent_items(self, lookup):
        """Returns list of subscribers that have previously received the item.

        :param dict lookup: elastic query to filter the publish queue
        :return: list of subscribers and list of product codes per subscriber
        """
        req = ParsedRequest()
        subscribers = []
        subscriber_codes = {}
        associations = {}
        queued_items = list(get_resource_service("publish_queue").get(req=req, lookup=lookup))

        if len(queued_items) > 0:
            subscriber_ids = {}
            for queue_item in queued_items:
                subscriber_id = queue_item["subscriber_id"]
                if not subscriber_ids.get(subscriber_id):
                    subscriber_ids[subscriber_id] = False
                    if queue_item.get("destination", {}).get("delivery_type") == "content_api":
                        subscriber_ids[subscriber_id] = True

                subscriber_codes[subscriber_id] = queue_item.get("codes", [])
                if queue_item.get("associated_items"):
                    associations[subscriber_id] = list(
                        set(associations.get(subscriber_id, [])) | set(queue_item.get("associated_items", []))
                    )

            query = {"$and": [{config.ID_FIELD: {"$in": list(subscriber_ids.keys())}}]}
            subscribers = list(get_resource_service("subscribers").get(req=None, lookup=query))
            for s in subscribers:
                s["api_enabled"] = subscriber_ids.get(s.get(config.ID_FIELD))

        return subscribers, subscriber_codes, associations

    def filter_subscribers(self, doc, subscribers, target_media_type):
        """Filter subscribers to whom the current document is going to be delivered.

        :param doc: Document to publish/kill/correct
        :param subscribers: List of Subscribers that might potentially get this document
        :param target_media_type: Valid values are - Wire, Digital.
        :return: List of of filtered subscribers and list of product codes per subscriber.
        """
        filtered_subscribers = []
        subscriber_codes = {}
        existing_products = {
            p[config.ID_FIELD]: p for p in list(get_resource_service("products").get(req=None, lookup=None))
        }
        global_filters = deepcopy(
            [gf["cf"] for gf in self.filters.get("content_filters", {}).values() if gf["cf"].get("is_global", True)]
        )

        # apply global filters
        self.conforms_global_filter(global_filters, doc)

        for subscriber in subscribers:
            if target_media_type and subscriber.get("subscriber_type", "") != SUBSCRIBER_TYPES.ALL:
                can_send_digital = subscriber["subscriber_type"] == SUBSCRIBER_TYPES.DIGITAL
                if (
                    target_media_type == SUBSCRIBER_TYPES.WIRE
                    and can_send_digital
                    or target_media_type == SUBSCRIBER_TYPES.DIGITAL
                    and not can_send_digital
                ):
                    continue

            conforms, skip_filters = self.conforms_subscriber_targets(subscriber, doc)
            if not conforms:
                continue

            if not self.conforms_subscriber_global_filter(subscriber, global_filters):
                continue

            product_codes = self._get_codes(subscriber)
            subscriber_added = False
            subscriber["api_enabled"] = False
            # validate against direct products
            result, codes = self._validate_article_for_subscriber(doc, subscriber.get("products"), existing_products)
            if result:
                product_codes.extend(codes)
                if not subscriber_added:
                    filtered_subscribers.append(subscriber)
                    subscriber_added = True

            if content_api.is_enabled():
                # validate against api products
                result, codes = self._validate_article_for_subscriber(
                    doc, subscriber.get("api_products"), existing_products
                )
                if result:
                    product_codes.extend(codes)
                    subscriber["api_enabled"] = True
                    if not subscriber_added:
                        filtered_subscribers.append(subscriber)
                        subscriber_added = True

            if skip_filters and not subscriber_added:
                # if targeted subscriber and has api products then send it to api.
                if subscriber.get("api_products"):
                    subscriber["api_enabled"] = True
                filtered_subscribers.append(subscriber)
                subscriber_added = True

            # unify the list of codes by removing duplicates
            if subscriber_added:
                subscriber_codes[subscriber[config.ID_FIELD]] = list(set(product_codes))

        return filtered_subscribers, subscriber_codes

    def _validate_article_for_subscriber(self, doc, products, existing_products):
        """Validate the article for subscriber

        :param dict doc: Document to be validated
        :param list products: list of product ids
        :param dict existing_products: Product lookup
        :return tuple bool, list: Boolean flag to add subscriber or not and list of product codes.
        """
        add_subscriber, product_codes = False, []

        if not products:
            return add_subscriber, product_codes

        for product_id in products:
            # check if the product filter conforms with the story
            product = existing_products.get(product_id)

            if not product:
                continue

            if not self.conforms_product_targets(product, doc):
                continue

            if self.conforms_content_filter(product, doc):
                # gather the codes of products
                product_codes.extend(self._get_codes(product))
                add_subscriber = True

        return add_subscriber, product_codes

    def _filter_subscribers_for_associations(self, subscribers, doc, target_media_type, existing_associations):
        """Filter the subscriber for associations.

        :param list subscribers: list of subscriber that are going to receive parent item.
        :param dict doc: item with associations
        :param dict existing_associations: existing associations
        :param target_media_type: Valid values are - Wire, Digital.
        """
        associations = {}

        if not doc.get(ASSOCIATIONS) or not subscribers:
            return associations

        for assoc, item in doc.get(ASSOCIATIONS).items():
            if not item:
                continue

            assoc_subscribers = set()
            assoc_id = item.get(config.ID_FIELD)
            filtered_subscribers, subscriber_codes = self.filter_subscribers(
                item, deepcopy(subscribers), target_media_type
            )

            for subscriber in filtered_subscribers:
                # for the validated subscribers
                subscriber_id = subscriber.get(config.ID_FIELD)
                if not associations.get(subscriber_id):
                    associations[subscriber_id] = []

                associations[subscriber_id].append(assoc_id)
                assoc_subscribers.add(subscriber_id)

            for subscriber_id, items in existing_associations.items():
                # for the not validated associated item but previously published to the subscriber.
                if assoc_id in items and assoc_id not in associations.get(subscriber_id, []):
                    if not associations.get(subscriber_id):
                        associations[subscriber_id] = []

                    associations[subscriber_id].append(assoc_id)
                    assoc_subscribers.add(subscriber_id)

            item["subscribers"] = list(assoc_subscribers)

        return associations

    def _update_associations(self, original, updates):
        """Update the associations

        :param dict original: original item
        :param dict updates: updates item
        """
        if not updates:
            return

        for subscriber, items in updates.items():
            if items:
                original[subscriber] = list(set(original.get(subscriber, [])) | set(updates.get(subscriber, [])))

    def conforms_product_targets(self, product, article):
        """Check product targets.

        Checks if the given article has any target information and if it does
        it checks if the product satisfies any of the target information

        :param product: Product to test
        :param article: article
        :return:
            bool: True if the article conforms the targets for the given product
        """
        geo_restrictions = product.get("geo_restrictions")

        # If not targeted at all then Return true
        if not BasePublishService().is_targeted(article, "target_regions"):
            return geo_restrictions is None

        if geo_restrictions:
            for region in article.get("target_regions", []):
                if region["qcode"] == geo_restrictions and region["allow"]:
                    return True
                if region["qcode"] != geo_restrictions and not region["allow"]:
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
        if not BasePublishService().is_targeted(article, "target_subscribers") and not BasePublishService().is_targeted(
            article, "target_types"
        ):
            return True, False

        subscriber_type = subscriber.get("subscriber_type")

        for t in article.get("target_subscribers", []):
            if str(t.get("_id")) == str(subscriber["_id"]):
                return True, True

        if subscriber_type:
            for t in article.get("target_types", []):
                if t["qcode"] == subscriber_type and t["allow"]:
                    return True, False
                if t["qcode"] != subscriber_type and not t["allow"]:
                    return True, False

        # If there's a region target then continue with the subscriber to check products
        if BasePublishService().is_targeted(article, "target_regions"):
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
        content_filter = product.get("content_filter")

        if content_filter is None or "filter_id" not in content_filter or content_filter["filter_id"] is None:
            return True

        service = get_resource_service("content_filters")
        filter = self.filters.get("content_filters", {}).get(content_filter["filter_id"], {}).get("cf")
        does_match = service.does_match(filter, doc, self.filters)

        if does_match:
            return content_filter["filter_type"] == "permitting"
        else:
            return content_filter["filter_type"] == "blocking"

    def conforms_global_filter(self, global_filters, doc):
        """Check global filter

        Checks if document matches the global filter

        :param global_filters: List of all global filters
        :param doc: Document to test the global filter against
        """
        service = get_resource_service("content_filters")
        for global_filter in global_filters:
            global_filter["does_match"] = service.does_match(global_filter, doc, self.filters)

    def conforms_subscriber_global_filter(self, subscriber, global_filters):
        """Check global filter for subscriber

        Checks if subscriber has a override rule against each of the
        global filter and if not checks if document matches the global filter

        :param subscriber: Subscriber to get if the global filter is overriden
        :param global_filters: List of all global filters
        :return: True if at least one global filter is not overriden
        and it matches the document
        False if global filter matches the document or all of them overriden
        """

        gfs = subscriber.get("global_filters", {})
        for global_filter in global_filters:
            if gfs.get(str(global_filter[config.ID_FIELD]), True):
                # Global filter applies to this subscriber
                if global_filter.get("does_match"):
                    return False
        return True

    def _extend_subscriber_items(self, subscriber_items, subscribers, item, package_item_id, subscriber_codes):
        """Extends the subscriber_items with the given list of subscribers for the item

        :param subscriber_items: The existing list of subscribers
        :param subscribers: New subscribers that item has been published to - to be added
        :param item: item that has been published
        :param package_item_id: package_item_id
        """
        item_id = item[config.ID_FIELD]
        for subscriber in subscribers:
            sid = subscriber[config.ID_FIELD]
            item_list = subscriber_items.get(sid, {}).get("items", {})
            item_list[item_id] = package_item_id
            subscriber_items[sid] = {
                "subscriber": subscriber,
                "items": item_list,
                "codes": subscriber_codes.get(sid, []),
            }

    def _get_codes(self, item):
        if item.get("codes"):
            return [c.strip() for c in item.get("codes").split(",") if c]
        else:
            return []

    @staticmethod
    def filter_document(doc):
        """
        Filter document:
        1. Remove fields that should not be there given it's profile.
        2. Remove `None` valued renditions.

        :param dict doc: document to filter
        :return: dict filtered document
        """

        # remove fields that should not be there given it's profile.
        doc = apply_schema(doc)

        # remove `None` valued renditions.
        for association_key in doc.get(ASSOCIATIONS, {}):
            association = doc[ASSOCIATIONS][association_key]
            if not association:
                continue

            renditions = association.get("renditions", {})
            for null_rendition_key in [k for k in renditions if not renditions[k]]:
                del doc[ASSOCIATIONS][association_key]["renditions"][null_rendition_key]

        return doc
