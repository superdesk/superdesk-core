# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk Publish

This module handles transmission of items to respective destinations.
Items must be inserted to publish queue in order to get transmitted.
"""

import logging
from typing import NamedTuple

from superdesk.celery_app import celery
from superdesk.publish.publish_content import PublishContent
from superdesk import get_backend

logger = logging.getLogger(__name__)

registered_transmitters = {}
transmitter_errors = {}
registered_transmitters_list = []


class SubscriberTypes(NamedTuple):
    DIGITAL: str
    WIRE: str
    ALL: str


SUBSCRIBER_TYPES: SubscriberTypes = SubscriberTypes("digital", "wire", "all")


class SubscriberMediaTypes(NamedTuple):
    MEDIA: str
    NONMEDIA: str
    BOTH: str


SUBSCRIBER_MEDIA_TYPES: SubscriberMediaTypes = SubscriberMediaTypes("media", "non-media", "both")


def register_transmitter(transmitter_type, transmitter, errors):
    registered_transmitters[transmitter_type] = transmitter
    transmitter_errors[transmitter_type] = dict(errors)
    registered_transmitters_list.append(
        {
            "type": transmitter_type,
            "name": transmitter.NAME or transmitter_type,
            "config": getattr(transmitter, "CONFIG", None),
        }
    )


@celery.task(soft_time_limit=1800, expires=10)
def transmit():
    """Transmit items from ``publish_queue`` collection."""
    PublishContent().run()


# must be imported for registration
from superdesk.publish.subscribers import SubscribersResource, SubscribersService  # NOQA
from superdesk.publish.publish_queue import PublishQueueResource, PublishQueueService  # NOQA
from superdesk.publish.subscriber_token import SubscriberTokenResource, SubscriberTokenService  # NOQA


def init_app(app):
    # XXX: we need to do imports for transmitters and formatters here
    #      so classes creation is done after PublishService is set
    #      this is a temporary workaround until a proper plugin system
    #      is implemented in Superdesk
    import superdesk.publish.transmitters  # NOQA
    import superdesk.publish.formatters  # NOQA

    endpoint_name = "subscribers"
    service = SubscribersService(endpoint_name, backend=get_backend())
    SubscribersResource(endpoint_name, app=app, service=service)

    endpoint_name = "publish_queue"
    service = PublishQueueService(endpoint_name, backend=get_backend())
    PublishQueueResource(endpoint_name, app=app, service=service)

    superdesk.register_resource("subscriber_token", SubscriberTokenResource, SubscriberTokenService)

    app.client_config.update(
        {
            "transmitter_types": registered_transmitters_list,
        }
    )
