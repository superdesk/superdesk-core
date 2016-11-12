from superdesk.resource import Resource
from superdesk import get_resource_service
from eve.utils import ParsedRequest
import json
from superdesk.services import BaseService
from superdesk.metadata.item import metadata_schema
from datetime import datetime


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
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {
                            "must": [
                                {"term": {"operation": report.operation}},
                                {"term": {"task.desk": str(report.desk)}},
                                {"term": {"subject.name": report.subject}},
                                {"term": {"keywords": report.keywords}}
                            ]
                        }
                    }
                }
            }
        }

        request = ParsedRequest
        request.args = {'source': json.dumps(query), 'repo': 'archive,published,archived,ingest'}
        items_list = list(get_resource_service('search').get(req=request, lookup=None))
        return len(items_list)

    def create(self, docs):
        for doc in docs:
            doc['timestamp'] = datetime.now()
            doc['report'] = self.search_items(doc)
        docs = super().create(docs)
        return docs
