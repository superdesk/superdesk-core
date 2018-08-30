
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2018 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""This module contains tools to help using Elastic Search"""

import logging
import json
from superdesk import app

logger = logging.getLogger(__name__)

REPOS = ['ingest', 'archive', 'published', 'archived']
POST_FILTER_MAP = {
    "type": "type",
    "desk": "task.desk",
    "genre": "genre.name",
    "category": "anpa_category.name",
    "urgency": "urgency",
    "priority": "priority",
    "source": "source",
    "legal": "flags.marked_for_legal",
    "sms": "flags.marked_for_sms",
    "language": "language",
}
SEARCH_CVS = [
    {'id': 'subject',
     'name': 'Subject',
     'field': 'subject',
     'list': 'subjectcodes'},
    {'id': 'companycodes',
     'name': 'Company Codes',
     'field': 'company_codes',
     'list': 'company_codes'}]


def get_index(repos=None):
    """Get index id for all repos."""
    if repos is None:
        repos = REPOS
    indexes = {app.data.elastic.index}
    for repo in repos:
        indexes.add(app.config['ELASTICSEARCH_INDEXES'].get(repo, app.data.elastic.index))
    return ','.join(indexes)


def get_docs(query_result):
    """Get documents from ES query result

    :param dict query_result: ES query result, as returned by service.search
    :return list: found documents
    """
    try:
        docs = [h['_source'] for h in query_result['hits']['hits']]
    except KeyError:
        logger.warning(u"Can't retrieve doc from ES results: {data}".format(data=query_result))
        docs = []
    return docs


def filter2query(filter_, user_id=None):
    """Convert filter syntax to ElasticSearch query

    :param dict filter_: filter syntax, as used in saved_searches endpoint
    :return dict: ElasticSearch query DSL usable with service.search method
    """
    # we'll delete key while we handle them, to check that all has been managed at the end
    search_query = filter_['query'].copy()
    query_must = []
    query_must_not = []
    post_filter = []
    post_filter_must_not = []

    # controlled vocabularies can be overriden in settings
    search_cvs = app.config.get('search_cvs', SEARCH_CVS)

    for cv in search_cvs:
        if cv['id'] in search_query and cv['field'] != cv['id']:
            terms = json.loads(search_query.pop(cv['id']))
            query_must.append({"terms": {cv['field'] + ".qcode": terms}})

    try:
        query_string = search_query.pop('q')
    except KeyError:
        pass
    else:
        for cv in search_cvs:
            if cv['field'] != cv['id']:
                query_string.replace(cv['id'] + '.qcode:(', cv['field'] + 'q.code:(')
        query_must.append(
            {"query_string": {
                "query": query_string,
                "default_operator": "AND"}})

    to_delete = []
    for key, value in search_query.items():
        if key == 'from_desk':
            desk = value.split('-')
            if len(desk) == 2:
                if desk[1] == 'authoring':
                    query_must.append({'term': {'task.last_authoring_desk': desk[0]}})
                else:
                    query_must.append({'term': {'task.last_production_desk': desk[0]}})
            else:
                logger.warning('unexpected "from_desk" value: {value}'.format(value=value))
        elif key == 'to_desk':
            desk = value.split('-')
            if len(desk) == 2:
                query_must.append({'term': {'task.desk': desk[0]}})
                if 'from_desk' not in filter_['query']:
                    if desk[1] == 'authoring':
                        field = 'task.last_production_desk'
                    else:
                        field = 'task.last_authoring_desk'
                    query_must.append({'exists': {field: field}})
            else:
                logger.warning('unexpected "from_desk" value: {value}'.format(value=value))
        elif key == 'spike':
            if value == 'include':
                pass
            elif value == 'only':
                query_must.append({"term": {"state": "spiked"}})
            else:
                query_must_not.append({"term": {"state": "spiked"}})
        elif key == 'featuremedia' and value:
            query_must.append({"exists": {"field": "associations.featuremedia"}})
        elif key == 'subject':
            terms = json.loads(value)
            query_must.append({"bool": {
                "should": [
                    {"terms": {"subject.qcode": terms}},
                    {"terms": {"subject.parent": terms}}],
                "minimum_should_match": 1}})
        elif key == 'company_codes':
            terms = json.loads(value)
            query_must.append({"terms": {"company_codes.qcode": terms}})
        elif key == 'marked_desks':
            terms = json.loads(value)
            query_must.append({"terms": {"marked_desks.desk_id": terms}})
        elif key == 'ignoreKilled':
            query_must_not.append({"terms": {"state": ["killed", "recalled"]}})
        elif key == 'onlyLastPublished':
            query_must_not.append({"term": {"last_published_version": "false"}})
        elif key == 'ignoreScheduled':
            query_must_not.append({"term": {"state": "scheduled"}})
        else:
            continue
        to_delete.append(key)

    for key in to_delete:
        del search_query[key]

    for key, field in POST_FILTER_MAP.items():
        value = search_query.pop(key, None)
        if value is not None:
            post_filter.append({'terms': {field: json.loads(value)}})
        else:
            value = search_query.pop('not' + key, None)
            if value is not None:
                post_filter_must_not.append({'terms': {field: json.loads(value)}})

    # used by AAP multimedia datalayer
    credit_qcode = search_query.pop('creditqcode', None)
    if credit_qcode is not None:
        values = json.loads(credit_qcode)
        post_filter.append({'terms': {'credit': [v['value'] for v in values]}})

    # remove other users drafts
    if user_id is not None:
        query_must.append({"bool": {
            "should": [
                {"bool": {
                    "must": [
                        {"term": {"state": "draft"}},
                        {"term": {"original_creator": user_id}}]}},
                {"bool": {
                    "must_not": {"terms": {"state": ["draft"]}}}}]}})

    # this is needed for archived collection
    query_must_not.append({"term": {"package_type": "takes"}})

    query = {
        "query": {
            "bool": {
                "must": query_must,
                "must_not": query_must_not
            }
        }
    }
    if post_filter or post_filter_must_not:
        query['post_filter'] = {"bool": {
            "must": post_filter,
            "must_not": post_filter_must_not}}

    if search_query:
        logger.warning("All query fields have not been used, remaining fields: {search_query}".format(
            search_query=search_query))

    return query
