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
    # check if some fields are filled out before generating the report and initiate the filter
    def check_for_fields(self, report):
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

    # get the list of all items in the 4 repos
    def get_items_list(self, query):
            request = ParsedRequest()
            request.args = {'source': json.dumps(query), 'repo': 'archive,published,archived,ingest'}
            items_list = list(get_resource_service('search').get(req=request, lookup=None))
            return items_list

    def search_items_without_groupping(self, report):
        terms = []
        terms.append({"term": {"task.desk": str(report['desk'])}})
        terms.append(self.check_for_fields(report))

        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": terms}
                    }
                }
            }
        }

        items_list = self.get_items_list(query)
        return {'items': len(items_list)}

    def search_items_when_groupping(self, report):
        result_list = []
        desks = get_resource_service('desks').get(req=None, lookup={})

        # return the filtered items for each desk
        for desk in desks:
            terms = []
            terms.append({"term": {"task.desk": str(desk['_id'])}})
            terms.append(self.check_for_fields(report))
            query = {
                "query": {
                    "filtered": {
                        "filter": {
                            "bool": {"must": terms}
                        }
                    }
                }
            }
            items_list = self.get_items_list(query)
            item = {'desk': desk['name'], 'items': len(items_list)}
            result_list.append(item)
        return result_list

    def create(self, docs):
        for doc in docs:
            doc['timestamp'] = datetime.now()
            if doc.get('group_by'):
                doc['report'] = self.search_items_when_groupping(doc)
            else:
                doc['report'] = self.search_items_without_groupping(doc)
        docs = super().create(docs)
        return docs
