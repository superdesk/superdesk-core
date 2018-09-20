# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from copy import deepcopy
from apps.tasks import send_to
from superdesk import register_resource, item_published, get_resource_service, privilege
from superdesk.services import Service
from superdesk.resource import Resource
from superdesk.errors import StopDuplication
from superdesk.metadata.item import PUBLISH_SCHEDULE, SCHEDULE_SETTINGS


NAME = 'internal_destinations'


class InternalDestinationsResource(Resource):
    schema = {
        'name': {'type': 'string', 'required': True},
        'is_active': {'type': 'boolean', 'required': True},
        'filter': Resource.rel('content_filters', nullable=True),
        'desk': Resource.rel('desks', nullable=False, required=True),
        'stage': Resource.rel('stages', nullable=True),
        'macro': {'type': 'string', 'nullable': True},
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

        new_item = deepcopy(item)
        send_to(new_item, desk_id=dest['desk'], stage_id=dest.get('stage'))

        if dest.get('macro'):
            macro = macros_service.get_macro_by_name(dest['macro'])
            try:
                macro['callback'](new_item)
            except StopDuplication:
                continue

        extra_fields = [PUBLISH_SCHEDULE, SCHEDULE_SETTINGS]
        archive_service.duplicate_content(new_item, state='routed', extra_fields=extra_fields)


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
