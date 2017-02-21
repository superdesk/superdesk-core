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
from superdesk.metadata.item import ITEM_STATE, CONTENT_TYPE, ITEM_TYPE, PUBLISH_STATES, GUID_FIELD, GUID_TAG
from superdesk.metadata.packages import SEQUENCE, PACKAGE_TYPE
from superdesk.notification import push_notification
from superdesk.services import BaseService
from superdesk.metadata.utils import item_url, generate_guid
from .common import get_user, get_expiry, item_operations, ITEM_OPERATION, set_sign_off
from superdesk.workflow import is_workflow_state_transition_valid
from apps.archive.archive import ArchiveResource, SOURCE as ARCHIVE
from apps.archive.common import ITEM_EVENT_ID, ITEM_UNLINK
from apps.packages import PackageService, TakesPackageService
from apps.archive.archive_rewrite import ArchiveRewriteService
from superdesk.metadata.packages import LINKED_IN_PACKAGES, PACKAGE
from superdesk.utc import get_expiry_date

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
        updates[ITEM_OPERATION] = ITEM_SPIKE
        self._validate_item(original)
        self._validate_take(original)
        self.update_rewrite(original)
        set_sign_off(updates, original=original)

    def _validate_item(self, original):
        """Validates that an item can be deleted.

        Raises an exception if the item is linked in a non-take package, the idea being that you don't whant to
        inadvertently remove the item from the packages, this force that to be done as a conscious action.

        :param original:
        :raise: An exception or nothing
        """
        packages = [x.get(PACKAGE) for x in original.get(LINKED_IN_PACKAGES, []) if not x.get(PACKAGE_TYPE)]
        if packages:
            query = {'$and': [{config.ID_FIELD: {'$in': packages}}]}
            cursor = get_resource_service(ARCHIVE).get_from_mongo(req=None, lookup=query)
            if cursor.count() > 0:
                raise SuperdeskApiError.badRequestError(
                    message="The item \"{}\" is in a package".format(original.get('slugline', '')) +
                            " it needs to be removed before the item can be spiked")

    def _validate_take(self, original):
        takes_service = TakesPackageService()
        if not takes_service.is_last_takes_package_item(original):
            raise SuperdeskApiError.badRequestError(message="Only last take of the package can be spiked.")

    def update_rewrite(self, original):
        """Removes the reference from the rewritten story in published collection."""
        rewrite_service = ArchiveRewriteService()
        if original.get('rewrite_of') and original.get(ITEM_EVENT_ID):
            rewrite_service._clear_rewritten_flag(original.get(ITEM_EVENT_ID),
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
        elif original.get('rewritten_by') or (takes_package and takes_package.get('rewritten_by')):
            # you are spike the story from which the rewrite was triggered.
            # in this case both rewrite_of and rewritten_by are published.
            rewrite_id = original.get('rewritten_by') or takes_package.get('rewritten_by')
            rewritten_by = archive_service.find_one(req=None, _id=rewrite_id)
            archive_service.system_update(rewrite_id, {'rewrite_of': None, 'rewrite_sequence': 0}, rewritten_by)
            app.on_archive_item_updated({'rewrite_of': None, 'rewrite_sequence': 0}, original, ITEM_UNLINK)

    def _removed_refs_from_package(self, item):
        """Remove reference from the package of the spiked item.

        :param item:
        """
        PackageService().remove_spiked_refs_from_package(item)

    def _get_spike_expiry(self, desk_id, stage_id):
        """Get spike expiry.

        If there is a SPIKE_EXPIRY_MINUTES setting then that is used to set the spike expiry.
        If a None value is configured then the desk/stage value is returned.
        :param desk_id:
        :param stage_id:
        :return:
        """
        # If no maximum spike expiry is set then return the desk/stage values
        if app.settings['SPIKE_EXPIRY_MINUTES'] is None:
            return get_expiry(desk_id=desk_id, stage_id=stage_id)
        else:
            return get_expiry_date(app.settings['SPIKE_EXPIRY_MINUTES'])

    def update(self, id, updates, original):
        original_state = original[ITEM_STATE]
        if not is_workflow_state_transition_valid(ITEM_SPIKE, original_state):
            raise InvalidStateTransitionError()

        user = get_user(required=True)
        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)
        task = item.get('task', {})

        updates[EXPIRY] = self._get_spike_expiry(desk_id=task.get('desk'), stage_id=task.get('stage'))
        updates[REVERT_STATE] = item.get(ITEM_STATE, None)

        if original.get('rewrite_of'):
            updates['rewrite_of'] = None

        if original.get('rewritten_by'):
            updates['rewritten_by'] = None

        if original.get('broadcast'):
            updates['broadcast'] = None

        if original.get('rewrite_sequence'):
            updates['rewrite_sequence'] = None

        # remove any relation with linked items
        updates[ITEM_EVENT_ID] = generate_guid(type=GUID_TAG)

        if original[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
            # remove links from items in the package
            package_service = PackageService()
            items = package_service.get_item_refs(original)
            for item in items:
                package_item = get_resource_service(ARCHIVE).find_one(req=None, _id=item[GUID_FIELD])
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

        history_updates = dict(updates)
        if original.get('task'):
            history_updates['task'] = original.get('task')
        app.on_archive_item_updated(history_updates, original, ITEM_SPIKE)
        self._removed_refs_from_package(id)
        return item

    def on_updated(self, updates, original):
        get_resource_service('archive_broadcast').spike_item(original)


class ArchiveUnspikeService(BaseService):

    def set_unspike_updates(self, doc, updates):
        """Generate changes for a given doc to unspike it.

        :param doc: document to unspike
        :param updates: updates dict
        """
        updates.update({
            REVERT_STATE: None,
            EXPIRY: None,
            ITEM_STATE: doc.get(REVERT_STATE),
            ITEM_OPERATION: ITEM_UNSPIKE,
        })

        task_info = updates.get('task', {})
        desk_id = task_info.get('desk')
        stage_id = task_info.get('stage')

        if not desk_id:  # no desk was set on unspike, restore previous
            desk_id = doc.get('task', {}).get('desk')
            stage_id = None

        if not stage_id and desk_id:  # get incoming stage for selected desk
            desk = app.data.find_one('desks', None, _id=desk_id)
            stage_id = desk['incoming_stage'] if desk else stage_id

        updates['task'] = {
            'desk': desk_id,
            'stage': stage_id,
            'user': None
        }

        updates[EXPIRY] = get_expiry(desk_id=desk_id, stage_id=stage_id)

    def on_update(self, updates, original):
        updates[ITEM_OPERATION] = ITEM_UNSPIKE
        updates[ITEM_STATE] = original.get(REVERT_STATE)
        set_sign_off(updates, original=original)

    def update(self, id, updates, original):
        original_state = original[ITEM_STATE]
        if not is_workflow_state_transition_valid(ITEM_UNSPIKE, original_state):
            raise InvalidStateTransitionError()

        user = get_user(required=True)
        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)

        self.set_unspike_updates(item, updates)
        self.backend.update(self.datasource, id, updates, original)

        item = get_resource_service(ARCHIVE).find_one(req=None, _id=id)
        push_notification('item:unspike', item=str(id), user=str(user.get(config.ID_FIELD)))
        app.on_archive_item_updated(updates, original, ITEM_UNSPIKE)

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
