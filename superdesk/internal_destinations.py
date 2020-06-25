# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

from copy import deepcopy
from apps.tasks import send_to
from superdesk import register_resource, get_resource_service, privilege
from superdesk.services import Service
from superdesk.resource import Resource
from superdesk.errors import StopDuplication
from superdesk.signals import item_published, item_routed
from superdesk.metadata.item import PUBLISH_SCHEDULE, SCHEDULE_SETTINGS


NAME = 'internal_destinations'

logger = logging.getLogger(__name__)


class InternalDestinationsResource(Resource):
    schema = {
        'name': {'type': 'string', 'required': True},
        'is_active': {'type': 'boolean', 'required': True},
        'filter': Resource.rel('content_filters', nullable=True),
        'desk': Resource.rel('desks', nullable=False, required=True),
        'stage': Resource.rel('stages', nullable=True),
        'macro': {'type': 'string', 'nullable': True},
        'send_after_schedule': {'type': 'boolean'},
    }

    privileges = {'POST': 'internal_destinations',
                  'PATCH': 'internal_destinations',
                  'DELETE': 'internal_destinations'}


class InternalDestinationsService(Service):
    pass


def handle_item_published(sender, item, **extra):
    macros_service = get_resource_service('macros')
    archive_service = get_resource_service('archive')
    filters_service = get_resource_service('content_filters')
    destinations_service = get_resource_service(NAME)

    for dest in destinations_service.get(req=None, lookup={'is_active': True}):
        if dest.get('desk') == item.get('task').get('desk'):
            # item desk and internal destination are same then don't execute
            continue

        if dest.get('filter'):
            content_filter = filters_service.find_one(req=None, _id=dest['filter'])
            if not content_filter:  # error state sort of, not sure what to do
                continue
            if not filters_service.does_match(content_filter, item):
                continue

        if dest.get('send_after_schedule', False) and item.get('state') != 'published':
            # if send_after_schedule is set to True and item state is other than published
            # then don't execute
            continue
        elif item.get('state') == 'published':
            item[PUBLISH_SCHEDULE] = None
            item[SCHEDULE_SETTINGS] = {}

        new_item = deepcopy(item)
        send_to(new_item, desk_id=dest['desk'], stage_id=dest.get('stage'))

        if dest.get('macro'):
            macro = macros_service.get_macro_by_name(dest['macro'])
            if not macro:
                logger.warning('macro %s not found for internal destination %s', dest['macro'], dest['name'])
            else:
                try:
                    macro['callback'](
                        new_item,
                        dest_desk_id=dest.get('desk'),
                        dest_stage_id=dest.get('stage'),
                    )
                except StopDuplication:
                    continue

        extra_fields = [PUBLISH_SCHEDULE, SCHEDULE_SETTINGS]
        next_id = archive_service.duplicate_item(new_item, state='routed', extra_fields=extra_fields)
        next_item = archive_service.find_one(req=None, _id=next_id)
        item_routed.send(sender, item=next_item)


def init_app(app):
    register_resource(
        NAME,
        InternalDestinationsResource,
        InternalDestinationsService,
        _app=app)

    privilege(
        name=NAME,
        label='Internal Destinations',
        description='User can manage internal destinations.')

    item_published.connect(handle_item_published)
