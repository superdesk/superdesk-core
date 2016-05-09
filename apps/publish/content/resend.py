# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.archive import ArchiveResource, SOURCE as ARCHIVE
from superdesk.metadata.utils import item_url
import logging
from functools import partial
from flask import request
from superdesk import get_resource_service, Service, config
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import CONTENT_TYPE, ITEM_TYPE, ITEM_STATE, CONTENT_STATE
from superdesk.publish import SUBSCRIBER_TYPES
from apps.publish.enqueue.enqueue_service import EnqueueService
from apps.archive.common import is_genre, BROADCAST_GENRE

logger = logging.getLogger(__name__)


class ResendResource(ArchiveResource):
    endpoint_name = 'archive_resend'
    resource_title = endpoint_name

    schema = {
        'subscribers': {'type': 'list'},
        'version': {'type': 'integer'}
    }

    url = 'archive/<{0}:original_id>/resend'.format(item_url)
    resource_methods = ['POST']
    privileges = {'POST': 'resend'}


class ResendService(Service):

    digital = partial(filter, lambda s: (s.get('subscriber_type', '') in {SUBSCRIBER_TYPES.DIGITAL,
                                                                          SUBSCRIBER_TYPES.ALL}))

    def create(self, docs, **kwargs):
        doc = docs[0] if len(docs) > 0 else {}
        article_id = request.view_args['original_id']
        article_version = doc.get('version')
        article = self._validate_article(article_id, article_version)
        subscribers = self._validate_subscribers(doc.get('subscribers'), article)
        EnqueueService().resend(article, subscribers)
        return [article_id]

    def _validate_subscribers(self, subscriber_ids, article):
        if not subscriber_ids:
            raise SuperdeskApiError.badRequestError(message='No subscribers selected!')

        query = {'$and': [{config.ID_FIELD: {'$in': list(subscriber_ids)}}, {'is_active': True}]}
        subscribers = list(get_resource_service('subscribers').get(req=None, lookup=query))

        if len(subscribers) == 0:
            raise SuperdeskApiError.badRequestError(message='No active subscribers found!')

        if is_genre(article, BROADCAST_GENRE):
            digital_subscribers = list(self.digital(subscribers))
            if len(digital_subscribers) > 0:
                raise SuperdeskApiError.badRequestError('Only wire subscribers can receive broadcast stories!')

        return subscribers

    def _validate_article(self, article_id, article_version):
        archive_article = get_resource_service(ARCHIVE).find_one(req=None, _id=article_id)

        if not archive_article:
            raise SuperdeskApiError.badRequestError(message="Story couldn't be found!")

        if archive_article[ITEM_TYPE] not in [CONTENT_TYPE.TEXT, CONTENT_TYPE.PREFORMATTED]:
            raise SuperdeskApiError.badRequestError(
                message='Only text stories can be resent!')

        if archive_article.get(ITEM_STATE) not in \
                [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED]:
            raise SuperdeskApiError.badRequestError(
                message='Only published, corrected or killed stories can be resent!')

        if archive_article[config.VERSION] != article_version:
            raise SuperdeskApiError.badRequestError(
                message='Please use the newest version {} to resend!'.format(archive_article[config.VERSION]))

        if archive_article.get('rewritten_by'):
            raise SuperdeskApiError.badRequestError(
                message='Updated story cannot be resent!')

        return archive_article
