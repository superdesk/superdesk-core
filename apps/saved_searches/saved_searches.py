# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import json

from eve.utils import ParsedRequest
from eve_elastic.elastic import build_elastic_query
from apps.archive.common import get_user
from superdesk import Resource, get_resource_service
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from superdesk.logging import logger
from superdesk.users.services import current_user_has_privilege
from apps.auth import get_user_id

UPDATE_NOTIFICATION = 'savedsearch:update'


def decode_filter(data):
    """Decode json in case it's string otherwise return data as is (dict).

    :param data
    """
    try:
        return json.loads(data)
    except TypeError:
        return data


def encode_filter(data):
    """Encode filter for storage.

    :param data
    """
    return json.dumps(data) if isinstance(data, dict) else data


def enhance_savedsearch(doc):
    """Decode the filter.

    :param dict doc: saved search
    :return None:
    """
    doc['filter'] = decode_filter(doc.get('filter'))


class SavedSearchesResource(Resource):
    endpoint_name = resource_title = 'saved_searches'
    schema = {
        'name': {
            'type': 'string',
            'required': True,
            'minlength': 1
        },
        'description': {
            'type': 'string'
        },
        'filter': {
            'type': 'dict',
            'required': True
        },
        'user': Resource.rel('users', nullable=True),
        'is_global': {
            'type': 'boolean',
            'default': False
        }
    }

    url = 'saved_searches'

    item_methods = ['GET', 'PATCH', 'DELETE']

    privileges = {'POST': 'saved_searches', 'PATCH': 'saved_searches', 'DELETE': 'saved_searches'}


class AllSavedSearchesResource(Resource):
    endpoint_name = resource_title = 'all_saved_searches'
    datasource = {'source': 'saved_searches'}
    resource_methods = ['GET']
    item_methods = []
    schema = SavedSearchesResource.schema


class AllSavedSearchesService(BaseService):
    def on_fetched_item(self, doc):
        enhance_savedsearch(doc)

    def on_fetched(self, docs):
        for doc in docs.get('_items', []):
            enhance_savedsearch(doc)


class SavedSearchesService(BaseService):
    def on_create(self, docs):
        for doc in docs:
            doc['user'] = get_user_id(required=True)
            self.process(doc)
        push_notification(UPDATE_NOTIFICATION)

    def process(self, doc):
        """
        Validates, constructs and runs the query in the document
        """
        repo, query = self.process_query(doc)
        if repo.find(',') >= 0:
            repo = repo.split(',').pop(0)
        self.validate_and_run_elastic_query(query, repo)
        doc['filter'] = encode_filter(doc.get('filter'))

    def on_update(self, updates, original):
        """Runs on update.

        Checks if the request owner and the saved search owner are the same person
        If not then the request owner should have global saved search privilege
        """
        self._validate_user(original.get('user', ''), original.get('is_global', False))
        if 'filter' in updates:
            self.process(updates)
        super().on_update(updates, original)
        push_notification(UPDATE_NOTIFICATION)

    def get(self, req, lookup):
        """
        Overriding to pass user as a search parameter
        """
        session_user = str(get_user_id(required=True))
        if not req:
            req = ParsedRequest()

        if lookup:
            req.where = json.dumps({'$or': [{'is_global': True}, {'user': session_user}, lookup]})
        else:
            req.where = json.dumps({'$or': [{'is_global': True}, {'user': session_user}]})

        return super().get(req, lookup=None)

    def init_request(self, elastic_query):
        """
        Initializes request object.
        """

        parsed_request = ParsedRequest()
        parsed_request.args = {"source": encode_filter(elastic_query)}

        return parsed_request

    def get_location(self, doc):
        """Returns location from the doc object and deletes it so that it's not passed to elastic query

        :param doc:
        :return: location
        """

        return doc['filter']['query'].get('repo', 'archive')

    def process_query(self, doc):
        """
        Processes the Saved Search document
        """

        if not doc['filter'].get('query'):
            raise SuperdeskApiError.badRequestError('Search cannot be saved without a filter!')

        return self.get_location(doc), build_elastic_query(
            {k: v for k, v in doc['filter']['query'].items() if k != 'repo'})

    def validate_and_run_elastic_query(self, elastic_query, index):
        """
        Validates the elastic_query against ElasticSearch.

        :param elastic_query: JSON format inline with ElasticSearch syntax
        :param index: Name of the ElasticSearch index
        :raise SuperdeskError: If failed to validate the elastic_query against ElasticSearch
        """

        parsed_request = self.init_request(elastic_query)
        try:
            return get_resource_service(index).get(req=parsed_request, lookup={})
        except Exception as e:
            logger.exception(e)
            raise SuperdeskApiError.badRequestError('Fail to validate the filter against %s.' % index)

    def on_fetched_item(self, doc):
        enhance_savedsearch(doc)

    def on_fetched(self, docs):
        for doc in docs.get('_items', []):
            enhance_savedsearch(doc)

    def on_deleted(self, doc):
        push_notification(UPDATE_NOTIFICATION)

    def on_delete(self, doc):
        self._validate_user(str(doc['user']), doc['is_global'])

    def _validate_user(self, doc_user_id, doc_is_global):
        session_user = get_user(required=True)
        if str(session_user['_id']) != str(doc_user_id):
            if not doc_is_global:
                raise SuperdeskApiError.forbiddenError('Unauthorized to modify other user\'s local search.')
            elif not current_user_has_privilege('global_saved_searches'):
                raise SuperdeskApiError.forbiddenError('Unauthorized to modify global search.')


class SavedSearchItemsResource(Resource):
    """Saved search items
    Since Eve doesn't support more than one URL for a resource, this resource is being created to fetch items based on
    the search string in the Saved Search document.
    """

    endpoint_name = 'saved_search_items'
    schema = SavedSearchesResource.schema

    resource_title = endpoint_name
    url = 'saved_searches/<regex("[a-zA-Z0-9:\\-\\.]+"):saved_search_id>/items'

    resource_methods = ['GET']
    item_methods = []


class SavedSearchItemsService(SavedSearchesService):
    def get(self, req, **lookup):
        saved_search_id = lookup['lookup']['saved_search_id']
        saved_search = get_resource_service('saved_searches').find_one(req=None, _id=saved_search_id)

        if not saved_search:
            raise SuperdeskApiError.notFoundError("Invalid Saved Search")

        saved_search['filter'] = decode_filter(saved_search.get('filter'))

        repo, query = super().process_query(saved_search)
        return super().validate_and_run_elastic_query(query, repo)
