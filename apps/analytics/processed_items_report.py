from superdesk import get_resource_service
from superdesk.services import BaseService

from superdesk.metadata.item import metadata_schema
from superdesk.resource import Resource


class ProcessedItemsResource(Resource):
    """Processed items schema
    """

    schema = {
        'user': metadata_schema['original_creator'],
        'starting_time': {'type': 'datetime'},
        'ending_time': {'type': 'datetime'},
        'report': {'type': 'dict'}
    }

    item_methods = ['GET', 'DELETE']
    resource_methods = ['POST']

    privileges = {'POST': 'processed_items_report', 'DELETE': 'processed_items_report', 'GET': 'processed_items_report'}


class ProcessedItemsService(BaseService):

    def create_query(self, report):
        """
        Returns a query on users.
        """
        archive_versions_query = {
            "task.user": str(report['user'])
        }
        return archive_versions_query

    def get_items(self, query):
        """
        Return the result of the item search by the given query.
        """
        return get_resource_service('archive_versions').get(req=None, lookup=query)

    def count_items(self, items_list, state, starting, ending):
        """
        Return the number of items which were modified in a given time interval and having a certain state.
        If no state is give, it will return all items modified in the given time interval.

        :param items_list: list of items based on the query
        :param state: item's state
        :param starting: starting time of the given interval
        :param ending: ending time of the given interval
        """
        if state == '':
            items = sum(1 for i in items_list
                        if (i['state'] in ['published', 'spiked', 'corrected', 'killed']) and
                        str(i['_updated']) >= str(starting) and str(i['_updated']) <= str(ending))
        else:
            items = sum(1 for i in items_list
                        if i['state'] == state and str(i['_updated']) >= str(starting) and
                        str(i['_updated']) <= str(ending))
        return items

    def search_items(self, doc):
        """
        Returns a report having:the total number of items processed by a given user and the number of published,
        spiked,corrected and killed items by a given user.

        :param query: query on user
        :param items: list of items based on the query
        :param total_items_no: total number of items processed by a user
        :param published_items_no: number of published items
        :param spiked_items_no: number of spiked items
        :param killed_items_no: number of killed items
        :param corrected_items_no: number of corrected items
        :param dict report: processed items report
        :return: report
        """
        query = self.create_query(doc)
        items = list(self.get_items(query))

        total_items_no = self.count_items(items, '',
                                          str(doc['starting_time']), str(doc['ending_time']))
        published_items_no = self.count_items(items, 'published',
                                              str(doc['starting_time']), str(doc['ending_time']))
        spiked_items_no = self.count_items(items, 'spiked',
                                           str(doc['starting_time']), str(doc['ending_time']))
        killed_items_no = self.count_items(items, 'killed',
                                           str(doc['starting_time']), str(doc['ending_time']))
        corrected_items_no = self.count_items(items, 'corrected',
                                              str(doc['starting_time']), str(doc['ending_time']))

        report = {'total_items': total_items_no,
                  'published_items': published_items_no,
                  'spiked_items': spiked_items_no,
                  'killed_items': killed_items_no,
                  'corrected_items': corrected_items_no}
        return report

    def create(self, docs):
        for doc in docs:
            doc['report'] = self.search_items(doc)
        docs = super().create(docs)
        return docs
