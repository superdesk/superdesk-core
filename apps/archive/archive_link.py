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
from superdesk.metadata.item import EMBARGO, ITEM_STATE, CONTENT_STATE, ITEM_TYPE, CONTENT_TYPE, GUID_TAG
from superdesk.resource import Resource, build_custom_hateoas
from apps.packages import TakesPackageService, PackageService
from apps.archive import ArchiveSpikeService
from apps.archive.common import CUSTOM_HATEOAS, BROADCAST_GENRE, is_genre, insert_into_versions, ITEM_UNLINK
from apps.auth import get_user
from superdesk.metadata.utils import item_url, generate_guid
from apps.archive.archive import SOURCE as ARCHIVE
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
import logging

logger = logging.getLogger(__name__)


class ArchiveLinkResource(Resource):
    endpoint_name = 'archive_link'
    resource_title = endpoint_name

    schema = {
        'link_id': Resource.rel('archive', embeddable=False, type='string', nullable=True, required=False),
        'desk': Resource.rel('desks', embeddable=False, nullable=True, required=False)
    }

    url = 'archive/<{0}:target_id>/link'.format(item_url)

    resource_methods = ['POST', 'DELETE']
    item_methods = []


class ArchiveLinkService(Service):
    packageService = TakesPackageService()

    def create(self, docs, **kwargs):
        target_id = request.view_args['target_id']
        doc = docs[0]
        link_id = doc.get('link_id')
        desk_id = doc.get('desk')
        service = get_resource_service(ARCHIVE)
        target = service.find_one(req=None, _id=target_id)
        self._validate_link(target, target_id)
        link = {}

        if desk_id:
            link = {'task': {'desk': desk_id}}
            user = get_user()
            lookup = {'_id': desk_id, 'members.user': user['_id']}
            desk = get_resource_service('desks').find_one(req=None, **lookup)
            if not desk:
                raise SuperdeskApiError.forbiddenError("No privileges to create new take on requested desk.")

            link['task']['stage'] = desk['working_stage']

        if link_id:
            link = service.find_one(req=None, _id=link_id)

        linked_item = self.packageService.link_as_next_take(target, link)
        insert_into_versions(id_=linked_item[config.ID_FIELD])
        doc.update(linked_item)
        build_custom_hateoas(CUSTOM_HATEOAS, doc)
        return [linked_item['_id']]

    def _validate_link(self, target, target_id):
        """Validates the article to be linked.

        :param target: article to be linked
        :param target_id: id of the article to be linked
        :raises: SuperdeskApiError
        """
        if not target:
            raise SuperdeskApiError.notFoundError(message='Cannot find the target item with id {}.'.format(target_id))

        if target.get(EMBARGO):
            raise SuperdeskApiError.badRequestError("Takes can't be created for an Item having Embargo")

        if is_genre(target, BROADCAST_GENRE):
            raise SuperdeskApiError.badRequestError("Cannot add new take to the story with genre as broadcast.")

        if get_resource_service('published').is_rewritten_before(target['_id']):
            raise SuperdeskApiError.badRequestError(message='Article has been rewritten before !')

    def _validate_unlink(self, target):
        """Validates that the links for takes or updates can be removed.

        :param target: article whose links will be removed
        :raises: SuperdeskApiError
        """
        if target[ITEM_TYPE] != CONTENT_TYPE.TEXT:
            raise SuperdeskApiError.badRequestError("Only text stories can be unlinked!")

        # if the story is in published states then it cannot be unlinked
        if target[ITEM_STATE] in [CONTENT_STATE.PUBLISHED, CONTENT_STATE.CORRECTED, CONTENT_STATE.KILLED]:
            raise SuperdeskApiError.badRequestError("Published stories cannot be unlinked!")

        # if the story is not the last take then it cannot be unlinked
        if TakesPackageService().get_take_package(target) and \
                not TakesPackageService().is_last_takes_package_item(target):
            raise SuperdeskApiError.badRequestError("Only the last take can be unlinked!")

    def on_delete(self, doc):
        self._validate_unlink(doc)

    def delete(self, lookup):
        target_id = request.view_args['target_id']
        archive_service = get_resource_service(ARCHIVE)
        target = archive_service.find_one(req=None, _id=target_id)
        self._validate_unlink(target)
        updates = {}

        takes_package = TakesPackageService().get_take_package(target)

        if takes_package and TakesPackageService().is_last_takes_package_item(target):
            # remove the take link
            PackageService().remove_refs_in_package(takes_package, target_id)

        if target.get('rewrite_of'):
            # remove the rewrite info
            ArchiveSpikeService().update_rewrite(target)

        if not takes_package and not target.get('rewrite_of'):
            # there is nothing to do
            raise SuperdeskApiError.badRequestError("Only takes and updates can be unlinked!")

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
