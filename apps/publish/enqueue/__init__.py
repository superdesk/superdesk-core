# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015, 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from superdesk.metadata.item import CONTENT_STATE
from apps.publish.enqueue.enqueue_corrected import EnqueueCorrectedService
from apps.publish.enqueue.enqueue_killed import EnqueueKilledService
from apps.publish.enqueue.enqueue_published import EnqueuePublishedService


logger = logging.getLogger(__name__)


UPDATE_SCHEDULE_DEFAULT = {"seconds": 10}

ITEM_PUBLISH = "publish"
ITEM_CORRECT = "correct"
ITEM_KILL = "kill"
ITEM_TAKEDOWN = "takedown"
ITEM_UNPUBLISH = "unpublish"
ITEM_BEING_CORRECTED = "being_corrected"

enqueue_services = {
    ITEM_PUBLISH: EnqueuePublishedService(),
    ITEM_CORRECT: EnqueueCorrectedService(),
    ITEM_BEING_CORRECTED: EnqueueCorrectedService(published_state=CONTENT_STATE.BEING_CORRECTED),
    ITEM_KILL: EnqueueKilledService(),
    ITEM_TAKEDOWN: EnqueueKilledService(published_state=CONTENT_STATE.RECALLED),
    ITEM_UNPUBLISH: EnqueueKilledService(published_state=CONTENT_STATE.UNPUBLISHED),
}


def get_enqueue_service(operation):
    try:
        enqueue_services[operation].get_filters()
    except KeyError:
        # Hot fix for https://dev.sourcefabric.org/browse/SDESK-3555
        # FIXME: this issue needs investigation and a proper fix.
        logger.error("unexpected operation: {operation}".format(operation=operation))
        operation = "correct"
        enqueue_services[operation].get_filters()
    return enqueue_services[operation]
