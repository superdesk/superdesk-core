# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.archive import ArchiveResource, SOURCE as ARCHIVE, remove_is_queued
from superdesk.metadata.utils import item_url
import logging
from functools import partial
from flask import request, current_app as app
from superdesk import get_resource_service, Service, config
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, ITEM_STATE, CONTENT_STATE
from superdesk.publish import SUBSCRIBER_TYPES
from apps.archive.common import is_genre, BROADCAST_GENRE, ITEM_RESEND
from apps.publish.enqueue import get_enqueue_service
from apps.archive.common import ITEM_OPERATION
from flask_babel import _

logger = logging.getLogger(__name__)


class ResendResource(ArchiveResource):
    endpoint_name = "archive_resend"
    resource_title = endpoint_name

    schema = {"subscribers": {"type": "list"}, "version": {"type": "integer"}}

    url = "archive/<{0}:original_id>/resend".format(item_url)
    resource_methods = ["POST"]
    privileges = {"POST": "resend"}


class ResendService(Service):

    digital = partial(
        filter, lambda s: (s.get("subscriber_type", "") in {SUBSCRIBER_TYPES.DIGITAL, SUBSCRIBER_TYPES.ALL})
    )

    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        article_id = request.view_args["original_id"]
        article_version = doc.get("version")
        article = self._validate_article(article_id, article_version)
        subscribers = self._validate_subscribers(doc.get("subscribers"), article)
        remove_is_queued(article)
        get_enqueue_service(article.get(ITEM_OPERATION)).resend(article, subscribers)
        app.on_archive_item_updated({"subscribers": doc.get("subscribers")}, article, ITEM_RESEND)
        return [article_id]

    def _validate_subscribers(self, subscriber_ids, article):
        if not subscriber_ids:
            raise SuperdeskApiError.badRequestError(message=_("No subscribers selected!"))

        query = {"$and": [{config.ID_FIELD: {"$in": list(subscriber_ids)}}, {"is_active": True}]}
        subscribers = list(get_resource_service("subscribers").get(req=None, lookup=query))

        if len(subscribers) == 0:
            raise SuperdeskApiError.badRequestError(message=_("No active subscribers found!"))

        if is_genre(article, BROADCAST_GENRE):
            digital_subscribers = list(self.digital(subscribers))
            if len(digital_subscribers) > 0:
                raise SuperdeskApiError.badRequestError(_("Only wire subscribers can receive broadcast stories!"))

        return subscribers

    def _validate_article(self, article_id, article_version):
        article = get_resource_service(ARCHIVE).find_one(req=None, _id=article_id)

        if app.config.get("CORRECTIONS_WORKFLOW") and article.get(ITEM_STATE) == "correction":
            publish_service = get_resource_service("published")
            article = publish_service.find_one(req=None, guid=article.get("guid"), state="being_corrected")

        if not article:
            raise SuperdeskApiError.badRequestError(message=_("Story couldn't be found!"))

        if article[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            raise SuperdeskApiError.badRequestError(message=_("Only text stories can be resent!"))

        if article.get(ITEM_STATE) not in [
            CONTENT_STATE.PUBLISHED,
            CONTENT_STATE.CORRECTED,
            CONTENT_STATE.KILLED,
            CONTENT_STATE.BEING_CORRECTED,
        ]:
            raise SuperdeskApiError.badRequestError(
                message=_("Only published, corrected or killed stories can be resent!")
            )

        if article[config.VERSION] != article_version:
            raise SuperdeskApiError.badRequestError(
                message=_("Please use the newest version {version} to resend!").format(version=article[config.VERSION])
            )

        if article.get("rewritten_by"):
            raise SuperdeskApiError.badRequestError(message=_("Updated story cannot be resent!"))

        return article
