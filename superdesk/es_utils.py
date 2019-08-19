
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
import pytz
from datetime import datetime
from superdesk import app

logger = logging.getLogger(__name__)

REPOS = ["ingest", "archive", "published", "archived"]
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
    {"id": "subject", "name": "Subject", "field": "subject", "list": "subjectcodes"},
    {"id": "companycodes", "name": "Company Codes", "field": "company_codes", "list": "company_codes"},
]
DATE_FORMAT = "%d/%m/%Y"
DATE_FILTERS = {
    "last_month": {"lte": "now-1M/M", "gte": "now-1M/M"},
    "last_week": {"lte": "now-1w/w", "gte": "now-1w/w"},
    "last_day": {"lte": "now-1d/d", "gte": "now-1d/d"},
    "last_24_hours": {"gte": "now-24H"},
    "last_7_hours": {"gte": "now-8H"},
}

DATE_FIELDS = ("firstcreated", "versioncreated", "firstpublished", "schedule_settings.utc_publish_schedule")


def get_index(repos=None):
    """Get index id for all repos."""
    if repos is None:
        repos = REPOS
    indexes = {app.data.elastic.index}
    for repo in repos:
        indexes.add(app.config["ELASTICSEARCH_INDEXES"].get(repo, app.data.elastic.index))
    return ",".join(indexes)


def get_docs(query_result):
    """Get documents from ES query result

    :param dict query_result: ES query result, as returned by service.search
    :return list: found documents
    """
    try:
        docs = [h["_source"] for h in query_result["hits"]["hits"]]
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
    search_query = filter_["query"].copy()
    query_must = []
    query_must_not = []
    post_filter = []
    post_filter_must_not = []

    # controlled vocabularies can be overriden in settings
    search_cvs = app.config.get("search_cvs", SEARCH_CVS)

    for cv in search_cvs:
        if cv["id"] in search_query and cv["field"] != cv["id"]:
            terms = json.loads(search_query.pop(cv["id"]))
            query_must.append({"terms": {cv["field"] + ".qcode": terms}})

    try:
        query_string = search_query.pop("q")
    except KeyError:
        pass
    else:
        for cv in search_cvs:
            if cv["field"] != cv["id"]:
                query_string.replace(cv["id"] + ".qcode:(", cv["field"] + "q.code:(")
        query_must.append({"query_string": {"query": query_string, "default_operator": "AND"}})

    to_delete = []
    for key, value in search_query.items():
        if key == "from_desk":
            desk = value.split("-")
            if len(desk) == 2:
                if desk[1] == "authoring":
                    query_must.append({"term": {"task.last_authoring_desk": desk[0]}})
                else:
                    query_must.append({"term": {"task.last_production_desk": desk[0]}})
            else:
                logger.warning('unexpected "from_desk" value: {value}'.format(value=value))
        elif key == "to_desk":
            desk = value.split("-")
            if len(desk) == 2:
                query_must.append({"term": {"task.desk": desk[0]}})
                if "from_desk" not in filter_["query"]:
                    if desk[1] == "authoring":
                        field = "task.last_production_desk"
                    else:
                        field = "task.last_authoring_desk"
                    query_must.append({"exists": {field: field}})
            else:
                logger.warning('unexpected "from_desk" value: {value}'.format(value=value))
        elif key == "spike":
            if value == "include":
                pass
            elif value == "only":
                query_must.append({"term": {"state": "spiked"}})
            else:
                query_must_not.append({"term": {"state": "spiked"}})
        elif key == "featuremedia" and value:
            query_must.append({"exists": {"field": "associations.featuremedia"}})
        elif key == "subject":
            terms = json.loads(value)
            query_must.append(
                {
                    "bool": {
                        "should": [{"terms": {"subject.qcode": terms}}, {"terms": {"subject.parent": terms}}],
                        "minimum_should_match": 1,
                    }
                }
            )
        elif key == "company_codes":
            terms = json.loads(value)
            query_must.append({"terms": {"company_codes.qcode": terms}})
        elif key == "marked_desks":
            terms = json.loads(value)
            query_must.append({"terms": {"marked_desks.desk_id": terms}})
        elif key == "ignoreKilled":
            query_must_not.append({"terms": {"state": ["killed", "recalled"]}})
        elif key == "onlyLastPublished":
            query_must_not.append({"term": {"last_published_version": "false"}})
        elif key == "ignoreScheduled":
            query_must_not.append({"term": {"state": "scheduled"}})
        elif key == "raw":
            query_must.append({
                "query_string": {
                    "query": value,
                    "lenient": False,
                    "default_operator": "AND",
                },
            })
        else:
            continue
        to_delete.append(key)

    for key in to_delete:
        del search_query[key]

    for key, field in POST_FILTER_MAP.items():
        value = search_query.pop(key, None)
        if value is not None:
            try:
                post_filter.append({"terms": {field: json.loads(value)}})
            except (ValueError, TypeError) as e:
                logger.warning('Invalid data received for post filter key="{key}" data="{value}" error="{e}"'.format(
                    key=key, e=e, value=value))
                # the value is probably not JSON encoded as expected, we try directly the value
                post_filter.append({"terms": {field: value}})
        else:
            value = search_query.pop("not" + key, None)
            if value is not None:
                post_filter_must_not.append({"terms": {field: json.loads(value)}})

    # ingest provider
    ingest_provider = search_query.pop("ingest_provider", None)
    if ingest_provider is not None:
        post_filter.append({"term": {"ingest_provider": ingest_provider}})

    # used by AAP multimedia datalayer
    credit_qcode = search_query.pop("creditqcode", None)
    if credit_qcode is not None:
        values = json.loads(credit_qcode)
        post_filter.append({"terms": {"credit": [v["value"] for v in values]}})

    # date filters
    tz = pytz.timezone(app.config["DEFAULT_TIMEZONE"])
    range_ = {}
    to_delete = []
    for field in DATE_FIELDS:
        value = search_query.get(field)
        if value in DATE_FILTERS:
            range_[field] = DATE_FILTERS[value]
            to_delete.append(field)
        else:
            field_suff = field + "to"
            value = search_query.get(field_suff)
            if value:
                to_delete.append(field_suff)
                field_range = range_.setdefault(field, {})
                try:
                    date = datetime.strptime(value, DATE_FORMAT)
                except ValueError:
                    # the value doesn't correspond to DATE_FORMAT,
                    # it may be using ES date math syntax
                    field_range["lte"] = value
                else:
                    date = tz.localize(datetime.combine(date, datetime.min.time()))
                    field_range["lte"] = date.isoformat()

            field_suff = field + "from"
            value = search_query.get(field_suff)
            if value:
                to_delete.append(field_suff)
                field_range = range_.setdefault(field, {})
                try:
                    date = datetime.strptime(value, DATE_FORMAT)
                except ValueError:
                    # same as above
                    field_range["gte"] = value
                else:
                    date = tz.localize(datetime.combine(date, datetime.max.time()))
                    field_range["gte"] = date.isoformat()

    if range_:
        post_filter.append({"range": range_})
    for key in to_delete:
        del search_query[key]

    # remove other users drafts
    if user_id is not None:
        query_must.append(
            {
                "bool": {
                    "should": [
                        {"bool": {"must": [{"term": {"state": "draft"}}, {"term": {"original_creator": user_id}}]}},
                        {"bool": {"must_not": {"terms": {"state": ["draft"]}}}},
                    ]
                }
            }
        )

    # this is needed for archived collection
    query_must_not.append({"term": {"package_type": "takes"}})

    query = {"query": {"bool": {"must": query_must, "must_not": query_must_not}}}
    if post_filter or post_filter_must_not:
        query["post_filter"] = {"bool": {"must": post_filter, "must_not": post_filter_must_not}}

    query["sort"] = {"versioncreated": "desc"}

    search_query.pop("repo", None)

    if "params" in search_query and (search_query['params'] is None or not json.loads(search_query['params'])):
        del search_query['params']

    if search_query:
        logger.warning(
            "All query fields have not been used, remaining fields: {search_query}".format(search_query=search_query)
        )

    return query


def filter2repos(filter_):
    try:
        return filter_['query']['repo']
    except KeyError:
        return None


def get_doc_types(selected_repos, all_repos=None):
    """Get document types for the given query."""
    if all_repos is None:
        all_repos = REPOS

    # If not repos were supplied, return all
    if selected_repos is None:
        return all_repos.copy()

    repos = selected_repos.split(',')

    # If the repos array is still empty after filtering, then return the default repos
    return [repo for repo in repos if repo in all_repos] or all_repos.copy()
