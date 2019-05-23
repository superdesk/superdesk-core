# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from eve.utils import config
from flask import request, current_app as app

from superdesk import get_resource_service, Service
from superdesk.metadata.item import GUID_TAG
from superdesk.resource import Resource
from apps.archive import ArchiveSpikeService
from apps.archive.common import ITEM_UNLINK
from apps.auth import get_user
from superdesk.metadata.utils import item_url, generate_guid
from apps.archive.archive import SOURCE as ARCHIVE
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
import logging
from flask_babel import _

logger = logging.getLogger(__name__)


class ArchiveLinkResource(Resource):
    endpoint_name = 'archive_link'
    resource_title = endpoint_name

    schema = {
        'link_id': Resource.rel('archive', embeddable=False, type='string', nullable=True, required=False),
        'desk': Resource.rel('desks', embeddable=False, nullable=True, required=False)
    }

    url = 'archive/<{0}:target_id>/link'.format(item_url)

    resource_methods = ['DELETE']
    item_methods = []


class ArchiveLinkService(Service):

    def delete(self, lookup):
        target_id = request.view_args['target_id']
        archive_service = get_resource_service(ARCHIVE)
        target = archive_service.find_one(req=None, _id=target_id)
        updates = {}

        if target.get('rewrite_of'):
            # remove the rewrite info
            ArchiveSpikeService().update_rewrite(target)

        if not target.get('rewrite_of'):
            # there is nothing to do
            raise SuperdeskApiError.badRequestError(_("Only updates can be unlinked!"))

        if target.get('rewrite_of'):
            updates['rewrite_of'] = None

        if target.get('anpa_take_key'):
            updates['anpa_take_key'] = None

        if target.get('rewrite_sequence'):
            updates['rewrite_sequence'] = None

        if target.get('sequence'):
            updates['sequence'] = None

        updates['event_id'] = generate_guid(type=GUID_TAG)

        archive_service.system_update(target_id, updates, target)
        user = get_user(required=True)
        push_notification('item:unlink', item=target_id, user=str(user.get(config.ID_FIELD)))
        app.on_archive_item_updated(updates, target, ITEM_UNLINK)
