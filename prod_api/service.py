# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import operator
from functools import reduce
import superdesk
from flask import current_app as app


class ProdApiService(superdesk.Service):
    """
    Base service for production api services
    """

    # specify fields to exclude from a response
    # NOTE: it's possible to specify nested key as `update._links.self.title`
    # in this case only item['update']['_links']['self']['title'] will be removed.
    excluded_fields = {
        '_etag',
        '_type',
        '_updated',
        '_created',
        '_current_version',
        '_links',
    }

    def on_fetched(self, result):
        """
        Event handler when a collection of items is retrieved from database.
        Post-process a fetched items.
        :param dict result: dictionary contaning the list of fetched items and
         some metadata, e.g. pagination info.
        """
        for doc in result['_items']:
            self._process_fetched_object(doc)

    def on_fetched_item(self, doc):
        """
        Event handler when a single item is retrieved from a database.
        Post-process a fetched item.
        :param dict docs: fetched items from a database.
        """
        self._process_fetched_object(doc)

    def _process_fetched_object(self, doc):
        """
        Does some processing on the document fetched from database.
        :param dict document: MongoDB document to process
        """
        self._remove_excluded_fields(doc)
        self._process_item_renditions(doc)

    def _remove_excluded_fields(self, item):
        """
        Remove keys from an item
        """
        for key in self.excluded_fields:
            keys = key.split('.')
            if keys[:-1]:
                # pop last key only from `item`
                try:
                    reduce(operator.getitem, keys[:-1], item).pop(keys[-1], None)
                except KeyError:
                    pass
            item.pop(key, None)

    def _process_item_renditions(self, doc):
        """
        Replace `href` in `renditions` and in `body_html`
        """

        def _process(item):
            for _k, v in item.get('renditions', {}).items():
                if v and 'media' in v:
                    media = v.pop('media')
                    old_href = v.get('href')
                    new_href = app.media.url_for_media(media, v.get('mimetype'))
                    v['href'] = new_href
                    # replace href in body
                    if old_href and doc.get('body_html'):
                        # no need to use lxml here, it will be to much
                        doc['body_html'] = doc['body_html'].replace(old_href, new_href)

        if doc.get('renditions'):
            _process(doc)

        for v in [v for v in doc.get('associations', {}).values() if v]:
            _process(v)
            self._remove_excluded_fields(v)
