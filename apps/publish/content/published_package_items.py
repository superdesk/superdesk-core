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
from eve.validation import ValidationError
from superdesk.errors import SuperdeskApiError
from superdesk.services import BaseService
from superdesk.metadata.packages import GROUPS, GROUP_ID, REFS, RESIDREF
from copy import deepcopy


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
                raise SuperdeskApiError.badRequestError('Invalid package identifier')
            if original[ITEM_STATE] not in PUBLISH_STATES:
                raise SuperdeskApiError.badRequestError('Package was not published')
            items = {}
            for new_item in doc['new_items']:
                item = get_resource_service(ARCHIVE).find_one(req=None, _id=new_item['item_id'])
                if not item:
                    raise SuperdeskApiError.badRequestError('Invalid item identifier %s' % new_item['item_id'])
                try:
                    self.package_service.check_for_circular_reference(original, new_item['item_id'])
                except ValidationError:
                    raise SuperdeskApiError.badRequestError('Circular reference in item %s', new_item['item_id'])
                items[item[config.ID_FIELD]] = item
    
            package = deepcopy(original)
            items_refs = []
            for new_item in doc['new_items']:
                create_root_group([package])
                items_refs.append(self._set_item_assoc(package, new_item, items[new_item['item_id']]))
            get_resource_service(ARCHIVE).system_update(package[config.ID_FIELD], package, original)
            for item_ref in items_refs:
                self.package_service.update_link(package, item_ref)
            ids.append(package[config.ID_FIELD])
        return ids

    def _set_item_assoc(self, package, new_item, item_doc):
        items_refs = []
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
        package[GROUPS].append({GROUP_ID: group, REFS: []})
        return package[GROUPS][-1]
