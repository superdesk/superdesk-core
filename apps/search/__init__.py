# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask import current_app as app, json, g
from eve_elastic.elastic import set_filters

import superdesk

from superdesk import get_resource_service
from superdesk.metadata.item import CONTENT_STATE, ITEM_STATE
from superdesk.metadata.utils import aggregations, item_url, get_elastic_highlight_query
from apps.archive.archive import SOURCE as ARCHIVE
from superdesk.resource import build_custom_hateoas


class SearchService(superdesk.Service):
    """Federated search service.

    It can search against different collections like Ingest, Production, Archived etc.. at the same time.
    """

    repos = ['ingest', 'archive', 'published', 'archived']

    @property
    def elastic(self):
        return app.data.elastic

    def __init__(self, datasource, backend):
        super().__init__(datasource=datasource, backend=backend)

    def _get_private_filters(self, repo, invisible_stages):
        query = {}
        if repo == 'ingest':
            query = {'and': [{'term': {'_type': 'ingest'}}]}
        elif repo == 'archive':
            user_id = g.get('user', {}).get('_id')
            query = {'and': [{'exists': {'field': 'task.desk'}},
                             {'bool': {
                                 'should': [
                                     {'and': [{'term': {ITEM_STATE: CONTENT_STATE.DRAFT}},
                                              {'term': {'task.user': str(user_id)}}]},
                                     {'terms': {ITEM_STATE: [CONTENT_STATE.FETCHED,
                                                             CONTENT_STATE.ROUTED,
                                                             CONTENT_STATE.PROGRESS,
                                                             CONTENT_STATE.SUBMITTED,
                                                             CONTENT_STATE.SPIKED]}},
                                 ],
                                 'must_not': {'term': {'version': 0}}
                             }}]}
        elif repo == 'published':
            query = {'and': [{'term': {'_type': 'published'}},
                             {'terms': {ITEM_STATE: [CONTENT_STATE.SCHEDULED,
                                                     CONTENT_STATE.PUBLISHED,
                                                     CONTENT_STATE.KILLED,
                                                     CONTENT_STATE.CORRECTED]}}]}
        elif repo == 'archived':
            query = {'and': [{'term': {'_type': 'archived'}}]}

        if invisible_stages and repo != 'ingest':
            query['and'].append({'not': {'terms': {'task.stage': invisible_stages}}})

        return query

    def _get_query(self, req):
        """Get elastic query."""
        args = getattr(req, 'args', {})
        query = json.loads(args.get('source')) if args.get('source') else {'query': {'filtered': {}}}
        if app.data.elastic.should_aggregate(req):
            query['aggs'] = aggregations

        if app.data.elastic.should_highlight(req):
            highlight_query = get_elastic_highlight_query(self._get_highlight_query_string(req))
            if highlight_query:
                query['highlight'] = highlight_query
        return query

    def _get_highlight_query_string(self, req):
        args = getattr(req, 'args', {})
        source = json.loads(args.get('source')) if args.get('source') else {'query': {'filtered': {}}}
        query_string = source.get('query', {}).get('filtered', {}).get('query', {}).get('query_string')
        return query_string

    def _get_projected_fields(self, req):
            """Get elastic projected fields."""
            if app.data.elastic.should_project(req):
                return app.data.elastic.get_projected_fields(req)

    def _get_types(self, req):
        """Get document types for the given query."""
        args = getattr(req, 'args', {})
        repos = args.get('repo')

        if repos is None:
            return self.repos.copy()
        else:
            repos = repos.split(',')
            return [repo for repo in repos if repo in self.repos]

    def _get_filters(self, repos, invisible_stages):
        """
        Gets filters for the passed repos.
        """
        filters = []

        for repo in repos:
            filters.append(self._get_private_filters(repo, invisible_stages))

        return [{'or': filters}]

    def get(self, req, lookup):
        """
        Runs elastic search on multiple doc types.
        """

        query = self._get_query(req)
        fields = self._get_projected_fields(req)
        types = self._get_types(req)

        user = g.get('user', {})
        if 'invisible_stages' in user:
            stages = user.get('invisible_stages')
        else:
            stages = get_resource_service('users').get_invisible_stages_ids(user.get('_id'))

        filters = self._get_filters(types, stages)

        # if the system has a setting value for the maximum search depth then apply the filter
        if not app.settings['MAX_SEARCH_DEPTH'] == -1:
            query['terminate_after'] = app.settings['MAX_SEARCH_DEPTH']

        set_filters(query, filters)

        params = {}
        if fields:
            params['_source'] = fields

        hits = self.elastic.es.search(body=query, index=self._get_index(), doc_type=types, params=params)
        docs = self._get_docs(hits)

        for resource in types:
            response = {app.config['ITEMS']: [doc for doc in docs if doc['_type'] == resource]}
            getattr(app, 'on_fetched_resource')(resource, response)
            getattr(app, 'on_fetched_resource_%s' % resource)(response)

        return docs

    def _get_docs(self, hits):
        """Parse hits from elastic and return only docs.

        This will remove some extra metadata from elastic.

        :param hits: elastic hits dictionary
        """
        return self.elastic._parse_hits(hits, 'ingest')  # any resource with item schema will do

    def find_one(self, req, **lookup):
        """Find item by id in all collections."""
        hits = self.elastic.es.mget({'ids': [lookup[app.config['ID_FIELD']]]}, self._get_index())
        hits['hits'] = {'hits': hits.pop('docs', [])}
        docs = self._get_docs(hits)
        return docs.first()

    def on_fetched(self, doc):
        """
        Overriding to add HATEOS for each individual item in the response.

        :param doc: response doc
        :type doc: dict
        """

        docs = doc[app.config['ITEMS']]
        for item in docs:
            build_custom_hateoas({'self': {'title': item['_type'], 'href': '/{}/{{_id}}'.format(item['_type'])}}, item)

    def _get_index(self):
        """Get index id for all repos."""
        indexes = {app.data.elastic.index}
        for repo in self.repos:
            indexes.add(app.config['ELASTICSEARCH_INDEXES'].get(repo, app.data.elastic.index))
        return ','.join(indexes)

    def get_available_indexes(self):
        """Returns a set of the configured indexes

        :return:
        """
        return set(self._get_index().split(','))


class SearchResource(superdesk.Resource):
    resource_methods = ['GET']
    item_methods = ['GET']
    item_url = item_url


def init_app(app):
    search_service = SearchService(ARCHIVE, backend=superdesk.get_backend())
    SearchResource('search', app=app, service=search_service)
