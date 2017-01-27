from superdesk import get_resource_service
from superdesk.services import BaseService

from eve.utils import ParsedRequest
from superdesk.metadata.item import metadata_schema
from superdesk.resource import Resource


class ProcessedItemsResource(Resource):
    """Processed items schema
    """

    schema = {
        'user': metadata_schema['original_creator'],
        'starting_time': {'type': 'datetime'},
        'ending_time': {'type': 'datetime'}
    }

    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']

    privileges = {'POST': 'processed_items_report', 'DELETE': 'processed_items_report', 'GET': 'processed_items_report'}


class ProcessedItemsService(BaseService):

    def create_query(self, doc):
        terms = [
            {"term": {"task.user": str(doc['user'])}}
        ]
        return terms

    def get_items(self, query):
        """Return the result of the item search by the given query
        """
        request = ParsedRequest()
        return get_resource_service('archive_versions').get(req=request, lookup=None)

    def count_items(self, query, state, starting, ending):
        """
        Return the number of items which was created in a given time interval and having a certain state.
        If no state is give, it will return all items created in the given time interval.
        """
        my_list = self.get_items(query)
        if state == '':
            items = sum(1 for i in my_list
                        if (i['state'] in ['published', 'spiked', 'corrected', 'killed', 'updated']) and
                        str(i['firstcreated']) >= str(starting) and str(i['firstcreated']) <= str(ending))
        else:
            items = sum(1 for i in my_list
                        if i['state'] == state and str(i['firstcreated']) >= str(starting) and
                        str(i['firstcreated']) <= str(ending))
        return items

    def search_without_grouping(self, doc):
        terms = self.create_query(doc)
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "bool": {"must": terms}
                    }
                }
            }
        }

        total_no_of_processed_items = self.count_items(query, '',
                                                       str(doc['starting_time']), str(doc['ending_time']))
        no_of_processed_items_published = self.count_items(query, 'published',
                                                           str(doc['starting_time']), str(doc['ending_time']))
        no_of_processed_items_spiked = self.count_items(query, 'spiked',
                                                        str(doc['starting_time']), str(doc['ending_time']))
        no_of_processed_items_updated = self.count_items(query, 'updated',
                                                         str(doc['starting_time']), str(doc['ending_time']))
        no_of_processed_items_killed = self.count_items(query, 'killed',
                                                        str(doc['starting_time']), str(doc['ending_time']))
        no_of_processed_items_corrected = self.count_items(query, 'corrected',
                                                           str(doc['starting_time']), str(doc['ending_time']))
        return {'total_no_of_processed_items': total_no_of_processed_items,
                'no_of_processed_items_published': no_of_processed_items_published,
                'no_of_processed_items_spiked': no_of_processed_items_spiked,
                'no_of_processed_items_updated': no_of_processed_items_updated,
                'no_of_processed_items_killed': no_of_processed_items_killed,
                'no_of_processed_items_corrected': no_of_processed_items_corrected}

    def create(self, docs):
        for doc in docs:
            doc['report'] = self.search_without_grouping(doc)
        docs = super().create(docs)
        return docs
