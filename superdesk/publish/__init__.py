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
from collections import namedtuple

from superdesk.celery_app import celery
from superdesk.publish.publish_content import PublishContent
from superdesk import get_backend


logger = logging.getLogger(__name__)

registered_transmitters = {}
transmitter_errors = {}

subscriber_types = ['digital', 'wire', 'all']
subscriber_media_types = ['media', 'non-media', 'both']
SUBSCRIBER_TYPES = namedtuple('SUBSCRIBER_TYPES', ['DIGITAL', 'WIRE', 'ALL'])(*subscriber_types)
SUBSCRIBER_MEDIA_TYPES = namedtuple('SUBSCRIBER_MEDIA_TYPES', ['MEDIA', 'NONMEDIA', 'BOTH'])(*subscriber_media_types)


def register_transmitter(transmitter_type, transmitter, errors):
    registered_transmitters[transmitter_type] = transmitter
    transmitter_errors[transmitter_type] = dict(errors)


@celery.task()
def transmit():
    PublishContent().run()


# must be imported for registration
from superdesk.publish.subscribers import SubscribersResource, SubscribersService  # NOQA
from superdesk.publish.publish_queue import PublishQueueResource, PublishQueueService  # NOQA


def init_app(app):
    # XXX: we need to do imports for transmitters and formatters here
    #      so classes creation is done after PublishService is set
    #      this is a temporary workaround until a proper plugin system
    #      is implemented in Superdesk
    import superdesk.publish.transmitters  # NOQA
    import superdesk.publish.formatters  # NOQA
    endpoint_name = 'subscribers'
    service = SubscribersService(endpoint_name, backend=get_backend())
    SubscribersResource(endpoint_name, app=app, service=service)

    endpoint_name = 'publish_queue'
    service = PublishQueueService(endpoint_name, backend=get_backend())
    PublishQueueResource(endpoint_name, app=app, service=service)
