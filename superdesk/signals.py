# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

__all__ = [
    'item_publish',
    'item_published',
    'item_update',
    'item_fetched',
    'item_moved',
]

import blinker

signals = blinker.Namespace()

#: Sent before item is published.
#:
#: .. versionadded:: 1.30
#:
#: :param sender: PublishService
#: :param item: item to publish
item_publish = signals.signal('item:publish')

#: Sent when item is published.
#:
#: :param sender: PublishService
#: :param item: published item
item_published = signals.signal('item:published')

#: Sent before new version is saved.
#:
#: :param sender: ArchiveService
#: :param updates: changes to be saved
#: :param original: original item version
item_update = signals.signal('item:update')

#: Sent after item is fetched.
#:
#: .. versionadded:: 1.29
#:
#: :param sender: FetchService
#: :param item: fetched item in production
#: :param ingest_item: item in ingest
item_fetched = signals.signal('item:fetched')

#: Sent after item is moved to different desk/stage.
#:
#: .. versionadded:: 1.29
#:
#: :param sender: MoveService
#: :param item: item after moving
#: :param original: item before moving
item_moved = signals.signal('item:moved')


#: Sent before item update is created
#:
#: .. versionadded:: 1.29
#:
#: :param sender: ArchiveRewriteService
#: :param item: new item update
#: :param original: original item
item_rewrite = signals.signal('item:rewrite')


#: Validate item
#:
#: You can add errors to response and that will
#: prevent publishing and display those errors to users.
#:
#: .. versionadded:: 1.30.1
#:
#: :param sender: ValidateService
#: :param item: item to validate
#: :param response: human readable list or errors
#: :param error_fields: system readable errors info
item_validate = signals.signal('item:validate')


def connect(signal, subscriber):
    """Connect to signal"""
    blinker.signal(signal).connect(subscriber)


def send(signal, sender, **kwargs):
    """Send signal"""
    return blinker.signal(signal).send(sender, **kwargs)


def proxy_resource_signal(action, app):
    def handle(resource, documents):
        docs = documents
        if '_items' in documents:
            docs = documents['_items']
        send(action, app.data, docs=docs)
        send('%s:%s' % (action, resource), app.data, docs=docs)
    return handle


def proxy_item_signal(action, app):
    def handle(resource, document):
        send(action, app.data, resource=resource, docs=[document])
        send('%s:%s' % (action, resource), app.data, docs=[document])
    return handle
