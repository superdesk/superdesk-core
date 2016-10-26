from superdesk.resource import Resource
from superdesk import get_resource_service
from eve.utils import ParsedRequest
import json
from superdesk.services import BaseService


class ActivityReportResource(Resource):
    """Activity Report schema
    """

    schema = {
        'desk': Resource.rel('desks', nullable=True),
        'operation': {
            'type': 'string'
        },
        'date': {
            'type': 'datetime'
        },
        'report': {
            'type': 'dict'
        }
    }
    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']
    privileges = {'POST': 'activityreports', 'DELETE': 'activityreports', 'GET': 'activityreports'}


class ActivityReportService(BaseService):

    def search_items(self, desk, operation, date):
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {
                            "must": [
                                {'range': {'created': {'gte': str(date),
                                                       'lte': str(date)}}},
                                {"term": {"operation": operation}},
                                {"term": {"task.desk": str(desk)}},
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
            operation = doc['operation']
            desk = doc['desk']
            date = doc['date']
            doc['report'] = self.search_items(desk, operation, date)
        docs = super().create(docs)
        return docs
