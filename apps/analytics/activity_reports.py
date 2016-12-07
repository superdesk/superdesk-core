# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime
import json
from superdesk import get_resource_service
from superdesk.services import BaseService

from eve.utils import ParsedRequest
from superdesk.metadata.item import metadata_schema
from superdesk.resource import Resource


class ActivityReportResource(Resource):
    """Activity Report schema
    """

    schema = {
        'desk': Resource.rel('desks', nullable=True),
        'operation': {'type': 'string'},
        'operation_date': {'type': 'datetime'},
        'subject': metadata_schema['subject'],
        'keywords': metadata_schema['keywords'],
        'group_by': {'type': 'list'},
        'report': {'type': 'dict'},
        'timestamp': {'type': 'datetime'},
        'force_regenerate': {'type': 'boolean', 'default': False}
    }
    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']
    privileges = {'POST': 'activity_reports', 'DELETE': 'activity_reports', 'GET': 'activity_reports'}


class ActivityReportService(BaseService):

    def search_items(self, report):
        print('report: ', report)
        terms = [
            {"term": {"operation": report['operation']}},
            {"term": {"task.desk": str(report['desk'])}}
        ]
        if report.get('subject'):
            subjects = [subject['name'] for subject in report['subject']]
            terms.append({'term': {'subject': subjects}})
        if report.get('keywords'):
            terms.append({'term': {'keywords': report['keywords']}})
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": terms}
                    }
                }
            }
        }
        print('query', query)

        request = ParsedRequest
        request.args = {'source': json.dumps(query), 'repo': 'archive,published,archived,ingest'}
        items_list = list(get_resource_service('archive').get(req=request, lookup=None))
        return [{'items': len(items_list)}]

    def create(self, docs):
        for doc in docs:
            doc['timestamp'] = datetime.now()
            doc['report'] = self.search_items(doc)
        docs = super().create(docs)
        return docs
