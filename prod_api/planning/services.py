# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask import current_app as app
from ..service import ProdApiService


class PlanningService(ProdApiService):
    excluded_fields = \
        {
            '_id',
            'item_class',
            'flags',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


class EventsService(ProdApiService):
    excluded_fields = \
        {
            '_id',
            'lock_action',
            'lock_user',
            'lock_time',
            'lock_session',
        } | ProdApiService.excluded_fields


class AssignmentsService(ProdApiService):
    excluded_fields = \
        {
            'lock_action',
            'lock_user',
            'lock_time',
        } | ProdApiService.excluded_fields


class EventsHistoryService(ProdApiService):
    excluded_fields = \
        {
            'update._etag',
            'update._links',
            'update._status',
            'update._updated',
            'update._created',
            'update._id',
        } | ProdApiService.excluded_fields


class EventsFilesService(ProdApiService):

    def on_fetched(self, result):
        super().on_fetched(result)
        self._join_fs_files(result)

    def _join_fs_files(self, result):
        db_fs_files = app.data.mongo.pymongo().db['fs.files']

        fs_files = {
            i['_id']: i for i in tuple(
                db_fs_files.find(
                    {
                        '_id': {
                            '$in': tuple(i['media'] for i in result.get('_items', []))
                        }
                    }
                )
            )
        }

        for item in result.get('_items', []):
            item['file'] = fs_files.get(item['media'], {})
