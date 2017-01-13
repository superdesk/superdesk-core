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
from superdesk.utils import format_date
from eve.default_settings import ID_FIELD


class ActivityReportResource(Resource):
    """Activity Report schema
    """

    schema = {
        'desk': Resource.rel('desks', nullable=True),
        'operation': {'type': 'string'},
        'operation_date': {'type': 'datetime'},
        'subject': metadata_schema['subject'],
        'keywords': metadata_schema['keywords'],
        'category': metadata_schema['anpa_category'],
        'urgency': metadata_schema['urgency'],
        'priority': metadata_schema['priority'],
        'subscriber': {'type': 'string'},
        'group_by': {'type': 'list'},
        'report': {'type': 'dict'},
        'timestamp': {'type': 'datetime'},
        'force_regenerate': {'type': 'boolean', 'default': False}
    }
    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']

    privileges = {'POST': 'activity_reports', 'DELETE': 'activity_reports', 'GET': 'activity_reports'}


class ActivityReportService(BaseService):
    def set_query_terms(self, report):
        """Check if some fields are filled out before generating the report and initiate the filter
        """
        terms = [
            {"term": {"operation": report['operation']}}
        ]
        if report.get('subject'):
            subjects = [subject['qcode'] for subject in report['subject']]
            terms.append({'terms': {'subject.qcode': subjects}})
        if report.get('keywords'):
            key = [x.lower() for x in report['keywords']]
            terms.append({'terms': {'keywords': key}})
        if report.get('operation_date'):
            op_date = format_date(report['operation_date'])
            terms.append({'range': {'versioncreated': {'gte': op_date, 'lte': op_date}}})
        if report.get('category'):
            categories = [category['qcode'] for category in report['category']]
            terms.append({'terms': {'anpa_category.qcode': categories}})
        if report.get('urgency'):
            urgency = report['urgency']
            terms.append({'terms': {'urgency': [urgency]}})
        if report.get('priority'):
            priority = report['priority']
            terms.append({'terms': {'priority': [priority]}})
        if report.get('subscriber'):
            subscriber = report['subscriber']
            terms.append({'terms': {'target_subscribers.name': [subscriber]}})

        return terms

    def get_items(self, query):
        """Return the result of the item search by the given query
        """
        request = ParsedRequest()
        request.args = {'source': json.dumps(query), 'repo': 'archive,published,archived,ingest'}
        return get_resource_service('search').get(req=request, lookup=None)

    def search_items_without_groupping(self, report):
        """Return the report without grouping by desk
        """
        terms = self.set_query_terms(report)
        terms.append({"term": {"task.desk": str(report['desk'])}})
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": terms}
                    }
                }
            }
        }
        return {'items': self.get_items(query).count()}

    def search_items_with_groupping(self, report):
        """Return the report without grouping by desk
        """
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": self.set_query_terms(report)}
                    }
                }
            }
        }
        items = self.get_items(query)

        if 'aggregations' in items.hits and 'desk' in items.hits['aggregations']:
            desk_buckets = items.hits['aggregations']['desk']['buckets']
        else:
            desk_buckets = []
        result_list = []
        for desk in get_resource_service('desks').get(req=None, lookup={}):
            desk_item_count = self._desk_item_count(desk_buckets, desk[ID_FIELD])
            result_list.append({'desk': desk['name'], 'items': desk_item_count})
        return result_list

    def _desk_item_count(self, bucket, desk_id):
        for desk_stats in bucket:
            if desk_stats['key'] == str(desk_id):
                return desk_stats['doc_count']
        return 0

    def create(self, docs):
        for doc in docs:
            doc['timestamp'] = datetime.now()
            if doc.get('group_by'):
                doc['report'] = self.search_items_with_groupping(doc)
            else:
                doc['report'] = self.search_items_without_groupping(doc)
        docs = super().create(docs)
        return docs
