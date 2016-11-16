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
        'date': {'type': 'datetime'},
        'report': {'type': 'dict'},
        'subject': metadata_schema['subject'],
        'keywords': metadata_schema['keywords'],
        'timestamp': {'type': 'datetime'},
        'force_regenerate': {'type': 'boolean', 'default': False}
    }
    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']
    privileges = {'POST': 'activity_reports', 'DELETE': 'activity_reports', 'GET': 'activity_reports'}


class ActivityReportService(BaseService):

    def search_items(self, desk, operation, subject, keywords):
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {
                            "must": [
                                {"term": {"operation": operation}},
                                {"term": {"task.desk": str(desk)}},
                                {"term": {"subject.name": subject}},
                                {"term": {"keywords": keywords}}
                            ]
                        }
                    }
                }
            }
        }

        request = ParsedRequest
        request.args = {'source': json.dumps(query), 'repo': 'archive,published,archived,ingest'}
        items_list = list(get_resource_service('archive').get(req=request, lookup=None))
        return len(items_list)

    def create(self, docs):
        for doc in docs:
            operation = doc['operation']
            desk = doc['desk']
            subject = doc['subject']
            keywords = doc['keywords']
            doc['timestamp'] = datetime.now()
#             date = doc['date']
            doc['report'] = self.search_items(desk, operation, subject, keywords)
        docs = super().create(docs)
        return docs
