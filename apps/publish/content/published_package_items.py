# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.archive.common import ARCHIVE
from superdesk import get_resource_service
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, PUBLISH_STATES, \
    ITEM_STATE
from superdesk.resource import Resource

from apps.packages.package_service import PackageService, create_root_group,\
    get_item_ref
from eve.utils import config
from superdesk.validation import ValidationError
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService
from superdesk.metadata.packages import GROUPS, GROUP_ID, REFS, RESIDREF,\
    ROOT_GROUP, ID_REF, PACKAGE_TYPE
from flask_babel import _


class PublishedPackageItemsResource(Resource):
    schema = {
        'package_id': {
            'type': 'string',
            'required': True
        },
        'new_items': {
            'type': 'list',
            'required': True,
            'schema': {
                'type': 'dict',
                'schema': {
                    'group': {'type': 'string'},
                    'item_id': {'type': 'string'}
                }
            }
        }
    }
    datasource = {
        'source': 'archive'
    }
    resource_methods = ['POST']
    privileges = {'POST': ARCHIVE}


class PublishedPackageItemsService(BaseService):
    package_service = PackageService()

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            original = get_resource_service(ARCHIVE).find_one(req=None, _id=doc['package_id'])
            if not original or original[ITEM_TYPE] != CONTENT_TYPE.COMPOSITE:
                raise SuperdeskApiError.badRequestError(_('Invalid package identifier'))
            if original[ITEM_STATE] not in PUBLISH_STATES:
                raise SuperdeskApiError.badRequestError(_('Package was not published'))

            items = {}
            for new_item in doc['new_items']:
                item = get_resource_service(ARCHIVE).find_one(req=None, _id=new_item['item_id'])
                if not item:
                    raise SuperdeskApiError.badRequestError(
                        _('Invalid item identifier  {item_id}').format(item_id=new_item['item_id']))
                try:
                    self.package_service.check_for_circular_reference(original, new_item['item_id'])
                except ValidationError:
                    raise SuperdeskApiError.badRequestError(
                        _('Circular reference in item {item_id}').format(item_id=new_item['item_id']))
                items[item[config.ID_FIELD]] = item

            updates = {key: original[key] for key in [config.ID_FIELD, PACKAGE_TYPE, GROUPS]
                       if key in original}
            create_root_group([updates])
            items_refs = []
            for new_item in doc['new_items']:
                items_refs.append(self._set_item_assoc(updates, new_item, items[new_item['item_id']]))
            get_resource_service(ARCHIVE).system_update(original[config.ID_FIELD], updates, original)
            for item_ref in items_refs:
                self.package_service.update_link(updates, item_ref)

            items_published = [new_item[ITEM_STATE] in PUBLISH_STATES for new_item in items.values()]
            if any(items_published):
                get_resource_service('archive_correct').patch(id=doc['package_id'], updates=updates)

            ids.append(original[config.ID_FIELD])
        return ids

    def _set_item_assoc(self, package, new_item, item_doc):
        group = self._get_group(package, new_item['group'])
        for assoc in group[REFS]:
            if assoc.get(RESIDREF) == new_item['item_id']:
                return assoc
        item_ref = get_item_ref(item_doc)
        group[REFS].append(item_ref)
        return item_ref

    def _get_group(self, package, group):
        for package_group in package[GROUPS]:
            if group == package_group[GROUP_ID]:
                return package_group
        self._add_group_in_root(group, package[GROUPS])
        package[GROUPS].append({GROUP_ID: group, REFS: []})
        return package[GROUPS][-1]

    def _add_group_in_root(self, group, groups):
        root_refs = []
        for group_meta in groups:
            if group_meta.get(GROUP_ID) == ROOT_GROUP:
                root_refs = [ref[ID_REF] for ref in group_meta[REFS]]
                if group not in root_refs:
                    group_meta[REFS].append({ID_REF: group})
