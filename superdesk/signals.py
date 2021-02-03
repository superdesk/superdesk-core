# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import blinker

__all__ = [
    "item_create",
    "item_publish",
    "item_published",
    "item_update",
    "item_updated",
    "item_fetched",
    "item_move",
    "item_moved",
    "item_rewrite",
    "item_validate",
    "item_routed",
    "item_duplicate",
    "item_duplicated",
    "archived_item_removed",
]

signals = blinker.Namespace()

#: Sent before item is created.
#:
#: .. versionadded:: 2.0
#:
#: :param sender: ArchiveService
#: :param item: item being created
item_create = signals.signal("item:create")

#: Sent before item is published.
#:
#: .. versionadded:: 1.30
#:
#: :param sender: PublishService
#: :param item: item to publish
item_publish = signals.signal("item:publish")

#: Sent when item is published.
#:
#: :param sender: PublishService
#: :param item: published item
item_published = signals.signal("item:published")

#: Sent before new version is saved.
#:
#: :param sender: ArchiveService
#: :param updates: changes to be saved
#: :param original: original item version
item_update = signals.signal("item:update")

#: Sent after new version is saved.
#:
#: .. versionadded:: 1.33
#:
#: :param sender: ArchiveService
#: :param item: updated item
#: :param original: original item version
item_updated = signals.signal("item:updated")

#: Sent after item is fetched.
#:
#: .. versionadded:: 1.29
#:
#: :param sender: FetchService
#: :param item: fetched item in production
#: :param ingest_item: item in ingest
item_fetched = signals.signal("item:fetched")

#: Sent before item is moved to different desk/stage.
#:
#: .. versionadded:: 1.33
#:
#: :param sender: MoveService
#: :param item: item after moving
#: :param original: item before moving
item_move = signals.signal("item:move")

#: Sent after item is moved to different desk/stage.
#:
#: .. versionadded:: 1.29
#:
#: :param sender: MoveService
#: :param item: item after moving
#: :param original: item before moving
item_moved = signals.signal("item:moved")


#: Sent before item update is created
#:
#: .. versionadded:: 1.29
#:
#: :param sender: ArchiveRewriteService
#: :param item: new item update
#: :param original: original item
item_rewrite = signals.signal("item:rewrite")


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
item_validate = signals.signal("item:validate")


#: Sent when item is routed via internal destinations
#:
#: .. versionadded:: 1.33
#:
#: :param sender: PublishService
#: :param item: new item created via routing
#:
item_routed = signals.signal("item:routed")


#: Sent before item is duplicated
#:
#: .. versionadded:: 2.0
#:
#: :param sender: ArchiveService
#: :param item: duplicated item to be saved
#: :param original: original item
#: :param operation: operation
item_duplicate = signals.signal("item:duplicate")


#: Sent after item is duplicated
#:
#: .. versionadded:: 2.0
#:
#: :param sender: ArchiveService
#: :param item: duplicated item
#: :param original: original item
#: :param operation: operation
item_duplicated = signals.signal("item:duplicated")


#: Sent then item is removed from archived
#:
#: ..versionadded:: 1.34
#:
#: :param sender: archived service
#: :param item: item being removed from archived
archived_item_removed = signals.signal("archived:removed")


def connect(signal, subscriber):
    """Connect to signal"""
    blinker.signal(signal).connect(subscriber)


def send(signal, sender, **kwargs):
    """Send signal"""
    return blinker.signal(signal).send(sender, **kwargs)


def proxy_resource_signal(action, app):
    def handle(resource, documents):
        docs = documents
        if "_items" in documents:
            docs = documents["_items"]
        send(action, app.data, docs=docs)
        send("%s:%s" % (action, resource), app.data, docs=docs)

    return handle


def proxy_item_signal(action, app):
    def handle(resource, document):
        send(action, app.data, resource=resource, docs=[document])
        send("%s:%s" % (action, resource), app.data, docs=[document])

    return handle
