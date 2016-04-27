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

from flask import current_app as app

import superdesk
from superdesk import get_resource_service, config
from superdesk.errors import SuperdeskApiError, InvalidStateTransitionError
from superdesk.metadata.item import ITEM_STATE, CONTENT_TYPE, ITEM_TYPE, PUBLISH_STATES,\
    PUBLISH_SCHEDULE, CONTENT_STATE
from superdesk.metadata.packages import SEQUENCE
from superdesk.notification import push_notification
from superdesk.services import BaseService
from superdesk.metadata.utils import item_url
from .common import get_user, get_expiry, item_operations, ITEM_OPERATION, \
    is_item_in_package, set_sign_off
from superdesk.workflow import is_workflow_state_transition_valid
from apps.archive.archive import ArchiveResource, SOURCE as ARCHIVE
from apps.packages import PackageService, TakesPackageService
from apps.archive.archive_rewrite import ArchiveRewriteService
from superdesk.metadata.packages import LINKED_IN_PACKAGES, PACKAGE

logger = logging.getLogger(__name__)

EXPIRY = 'expiry'
REVERT_STATE = 'revert_state'
ITEM_SPIKE = 'spike'
ITEM_UNSPIKE = 'unspike'
item_operations.extend([ITEM_SPIKE, ITEM_UNSPIKE])


class ArchiveSpikeResource(ArchiveResource):
    endpoint_name = 'archive_spike'
    resource_title = endpoint_name
    datasource = {'source': ARCHIVE}

    url = "archive/spike"
    item_url = item_url

    resource_methods = []
    item_methods = ['PATCH']

    privileges = {'PATCH': 'spike'}


class ArchiveUnspikeResource(ArchiveResource):
    endpoint_name = 'archive_unspike'
    resource_title = endpoint_name
    datasource = {'source': ARCHIVE}

    url = "archive/unspike"
    item_url = item_url

    resource_methods = []
    item_methods = ['PATCH']

    privileges = {'PATCH': 'unspike'}


class ArchiveSpikeService(BaseService):

    def on_update(self, updates, original):
        if PUBLISH_SCHEDULE in original and original[ITEM_STATE] == CONTENT_STATE.SCHEDULED:
            new_original = get_resource_service('archive').patch(original[config.ID_FIELD], {PUBLISH_SCHEDULE: None})
            original.update(new_original)
        updates[ITEM_OPERATION] = ITEM_SPIKE
        self._validate_item(original)
        self._validate_take(original)
        self._update_rewrite(original)
        set_sign_off(updates, original=original)

    def _validate_item(self, original):
        """
        Raises an exception if the item is linked in a non-take package, the idea being that you don't whant to
        inadvertently remove the item from the packages, this force that to be done as a conscious action.
        :param original:
        :raise: An exception or nothing
        """
        if is_item_in_package(original):
            raise SuperdeskApiError.badRequestError(
                message="The item \"{}\" is in a package".format(original.get('slugline', '')) +
                        " it needs to be removed before the item can be spiked")

    def _validate_take(self, original):
        takes_service = TakesPackageService()
        if not takes_service.is_last_takes_package_item(original):
            raise SuperdeskApiError.badRequestError(message="Only last take of the package can be spiked.")

    def _update_rewrite(self, original):
        """ Removes the reference from the rewritten story in published collection """
        rewrite_service = ArchiveRewriteService()
        if original.get('rewrite_of') and original.get('event_id'):
            rewrite_service._clear_rewritten_flag(original.get('event_id'),
                                                  original[config.ID_FIELD], 'rewritten_by')

        # write the rewritten_by to the take before spiked
        archive_service = get_resource_service(ARCHIVE)
        published_service = get_resource_service('published')
        takes_service = TakesPackageService()
        takes_package = takes_service.get_take_package(original)
        if takes_package and takes_package.get(SEQUENCE, 0) > 1 and original.get('rewritten_by'):
            # get the rewritten by
            rewritten_by = archive_service.find_one(req=None, _id=original.get('rewritten_by'))

            # get the take
            take_id = takes_service.get_take_by_take_no(original,
                                                        take_no=takes_package.get(SEQUENCE) - 1,
                                                        package=takes_package)
            take = archive_service.find_one(req=None, _id=take_id)

            # update the take and takes package with rewritten_by
            if take.get('rewritten_by') != rewritten_by[config.ID_FIELD]:
                if take.get(ITEM_STATE) in PUBLISH_STATES:
                    published_service.update_published_items(take_id, 'rewritten_by', rewritten_by[config.ID_FIELD])

                archive_service.system_update(take[config.ID_FIELD],
                                              {'rewritten_by': rewritten_by[config.ID_FIELD]}, take)

            if takes_package.get('rewritten_by') != rewritten_by[config.ID_FIELD]:
                if takes_package.get(ITEM_STATE) in PUBLISH_STATES:
                    published_service.update_published_items(takes_package.get(config.ID_FIELD),
                                                             'rewritten_by', rewritten_by[config.ID_FIELD])

                archive_service.system_update(takes_package[config.ID_FIELD],
                                              {'rewritten_by': rewritten_by[config.ID_FIELD]}, takes_package)

            if rewritten_by.get('rewrite_of') != takes_package.get(config.ID_FIELD):
                archive_service.system_update(rewritten_by[config.ID_FIELD],
                                              {'rewrite_of': takes_package.get(config.ID_FIELD)},
                                              rewritten_by)

    def _removed_refs_from_package(self, item):
        """
        Remove reference from the package of the spiked item
        :param item:
        """
        PackageService().remove_spiked_refs_from_package(item)

    def update(self, id, updates, original):
        original_state = original[ITEM_STATE]
        if not is_workflow_state_transition_valid('spike', original_state):
            raise InvalidStateTransitionError()

        user = get_user(required=True)
        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)
        task = item.get('task', {})

        updates[EXPIRY] = get_expiry(desk_id=task.get('desk'), stage_id=task.get('stage'))
        updates[REVERT_STATE] = item.get(ITEM_STATE, None)

        if original.get('rewrite_of'):
            updates['rewrite_of'] = None

        if original.get('rewritten_by'):
            updates['rewritten_by'] = None

        if original.get('broadcast'):
            updates['broadcast'] = None

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            # remove links from items in the package
            package_service = PackageService()
            items = package_service.get_item_refs(original)
            for item in items:
                package_item = get_resource_service(ARCHIVE).find_one(req=None, _id=item['guid'])
                if package_item:
                    linked_in_packages = [linked for linked in package_item.get(LINKED_IN_PACKAGES, [])
                                          if linked.get(PACKAGE) != original.get(config.ID_FIELD)]
                    super().system_update(package_item[config.ID_FIELD],
                                          {LINKED_IN_PACKAGES: linked_in_packages},
                                          package_item)

            # and remove all the items from the package
            updates['groups'] = []

        item = self.backend.update(self.datasource, id, updates, original)
        push_notification('item:spike', item=str(id), user=str(user.get(config.ID_FIELD)))
        self._removed_refs_from_package(id)
        return item

    def on_updated(self, updates, original):
        get_resource_service('archive_broadcast').spike_item(original)


class ArchiveUnspikeService(BaseService):

    def get_unspike_updates(self, doc):
        """Generate changes for a given doc to unspike it.

        :param doc: document to unspike
        """
        updates = {REVERT_STATE: None, EXPIRY: None, 'state': doc.get(REVERT_STATE),
                   ITEM_OPERATION: ITEM_UNSPIKE}

        desk_id = doc.get('task', {}).get('desk')
        stage_id = None
        if desk_id:
            desk = app.data.find_one('desks', None, _id=desk_id)
            stage_id = desk['incoming_stage']
            updates['task'] = {
                'desk': desk_id,
                'stage': stage_id if desk_id else None,
                'user': None
            }

        updates[EXPIRY] = get_expiry(desk_id=desk_id, stage_id=stage_id)
        return updates

    def on_update(self, updates, original):
        updates[ITEM_OPERATION] = ITEM_UNSPIKE
        set_sign_off(updates, original=original)

    def update(self, id, updates, original):
        original_state = original[ITEM_STATE]
        if not is_workflow_state_transition_valid('unspike', original_state):
            raise InvalidStateTransitionError()
        user = get_user(required=True)

        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)
        updates.update(self.get_unspike_updates(item))

        self.backend.update(self.datasource, id, updates, original)
        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)

        push_notification('item:unspike', item=str(id), user=str(user.get(config.ID_FIELD)))
        return item


superdesk.workflow_state('spiked')

superdesk.workflow_action(
    name='spike',
    exclude_states=['spiked', 'published', 'scheduled', 'corrected', 'killed'],
    privileges=['spike']
)

superdesk.workflow_action(
    name='unspike',
    include_states=['spiked'],
    privileges=['unspike']
)
