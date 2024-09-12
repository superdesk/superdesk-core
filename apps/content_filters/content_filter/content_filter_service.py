# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import logging

from superdesk.services import CacheableService
from eve.utils import ParsedRequest
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from apps.content_filters.filter_condition.filter_condition import FilterCondition
from flask_babel import _


logger = logging.getLogger(__name__)


class ContentFilterService(CacheableService):
    def get(self, req, lookup):
        if req is None:
            req = ParsedRequest()
        if req.args and req.args.get("is_global"):
            lookup = {"is_global": True}
        return self.backend.get(self.datasource, req=req, lookup=lookup)

    def update(self, id, updates, original):
        content_filter = dict(original)
        content_filter.update(updates)
        self._validate_no_circular_reference(content_filter, content_filter["_id"])
        super().update(id, updates, original)

    def delete(self, lookup):
        filter_id = lookup.get("_id")

        # check if the filter is referenced by any subscribers...
        subscribers = self._get_referencing_subscribers(filter_id)
        if len(subscribers) > 0:
            references = ",".join(s["name"] for s in subscribers)
            raise SuperdeskApiError.badRequestError(
                _("Content filter has been referenced by subscriber(s) {references}").format(references=references)
            )

        # check if the filter is referenced by any routing schemes...
        schemes = self._get_referencing_routing_schemes(filter_id)
        if schemes.count() > 0:
            references = ",".join(s["name"] for s in schemes)
            raise SuperdeskApiError.badRequestError(
                _("Content filter has been referenced by routing scheme(s) {references}").format(references=references)
            )

        # check if the filter is referenced by any other content filters...
        referenced_filters = self._get_content_filters_by_content_filter(filter_id)
        if referenced_filters.count() > 0:
            references = ",".join([pf["name"] for pf in referenced_filters])
            raise SuperdeskApiError.badRequestError(
                _("Content filter has been referenced in {references})").format(references=references)
            )

        return super().delete(lookup)

    def _get_content_filters_by_content_filter(self, content_filter_id):
        lookup = {"content_filter.expression.pf": {"$in": [content_filter_id]}}
        content_filters = get_resource_service("content_filters").get_from_mongo(req=None, lookup=lookup)
        return content_filters

    def _get_referencing_subscribers(self, filter_id):
        """Fetch all subscribers that contain a reference to the given filter.

        :param str filter_id: the referenced filter's ID
        :return: DB cursor over the results
        :rtype: :py:class:`pymongo.cursor.Cursor`
        """
        subscribers_service = get_resource_service("subscribers")
        products_service = get_resource_service("products")
        subscribers = []

        products = products_service.get_from_mongo(req=None, lookup={"content_filter.filter_id": filter_id})

        for p in products:
            subs = list(
                subscribers_service.get_from_mongo(
                    req=None, lookup={"$or": [{"products": p["_id"]}, {"api_products": p["_id"]}]}
                )
            )
            subscribers.extend(subs)

        return subscribers

    def _get_referencing_routing_schemes(self, filter_id):
        """Fetch all routing schemes that contain a reference to the given filter.

        :param str filter_id: the referenced filter's ID
        :return: DB cursor over the results
        :rtype: :py:class:`pymongo.cursor.Cursor`
        """
        routing_schemes_service = get_resource_service("routing_schemes")
        schemes = routing_schemes_service.get_from_mongo(req=None, lookup={"rules.filter": filter_id})
        return schemes

    def get_content_filters_by_filter_condition(self, filter_condition_id):
        lookup = {"content_filter.expression.fc": {"$in": [filter_condition_id]}}
        content_filters = list(super().get_from_mongo(req=None, lookup=lookup))
        all_content_filters = self._get_referenced_content_filters(content_filters, None)
        return all_content_filters

    def _get_referenced_content_filters(self, content_filters, pf_list):
        if not pf_list:
            pf_list = []

        for pf in content_filters:
            pf_list.append(pf)
            references = list(self._get_content_filters_by_content_filter(pf["_id"]))
            if references and len(references) > 0:
                return self._get_referenced_content_filters(references, pf_list)
        return pf_list

    def _validate_no_circular_reference(self, content_filter, filter_id):
        for expression in content_filter.get("content_filter", []):
            if "pf" in expression.get("expression", {}):
                for f in expression["expression"]["pf"]:
                    current_filter = super().find_one(req=None, _id=f)
                    if f == filter_id:
                        raise SuperdeskApiError.badRequestError(
                            _("Circular dependency error in content filters:{filter}").format(
                                filter=current_filter["name"]
                            )
                        )
                    self._validate_no_circular_reference(current_filter, filter_id)

    def build_mongo_query(self, doc):
        filter_condition_service = get_resource_service("filter_conditions")
        expressions = []
        for expression in doc.get("content_filter", []):
            filter_conditions = []
            if "fc" in expression.get("expression", {}):
                for f in expression["expression"]["fc"]:
                    current_filter = FilterCondition.parse(filter_condition_service.find_one(req=None, _id=f))
                    mongo_query = current_filter.get_mongo_query()
                    filter_conditions.append(mongo_query)
            if "pf" in expression.get("expression", {}):
                for f in expression["expression"]["pf"]:
                    current_filter = super().find_one(req=None, _id=f)
                    mongo_query = self.build_mongo_query(current_filter)
                    filter_conditions.append(mongo_query)

            if len(filter_conditions) > 1:
                expressions.append({"$and": filter_conditions})
            else:
                expressions.extend(filter_conditions)

        if len(expressions) > 1:
            return {"$or": expressions}
        else:
            return expressions[0]

    def build_elastic_query(self, doc):
        return {"query": {"filtered": {"query": self._get_elastic_query(doc)}}}

    def build_elastic_not_filter(self, doc):
        return {"query": {"filtered": {"query": self._get_elastic_query(doc, matching=False)}}}

    def _get_elastic_query(self, doc, matching=True):
        expressions_list = []
        if matching:
            expressions = {"should": expressions_list}
        else:
            expressions = {"must_not": expressions_list}

        filter_condition_service = get_resource_service("filter_conditions")
        for expression in doc.get("content_filter", []):
            filter_conditions = {"must": [], "must_not": [{"term": {"state": "spiked"}}]}
            if "fc" in expression.get("expression", {}):
                for f in expression["expression"]["fc"]:
                    current_filter = FilterCondition.parse(filter_condition_service.find_one(req=None, _id=f))
                    elastic_query = current_filter.get_elastic_query()
                    if current_filter.contains_not():
                        filter_conditions["must_not"].append(elastic_query)
                    else:
                        filter_conditions["must"].append(elastic_query)
            if "pf" in expression.get("expression", {}):
                for f in expression["expression"]["pf"]:
                    current_filter = super().find_one(req=None, _id=f)
                    elastic_query = self._get_elastic_query(current_filter)
                    filter_conditions["must"].append(elastic_query)

            expressions_list.append({"bool": filter_conditions})
        return {"bool": expressions}

    def does_match(self, content_filter, article, filters=None, cache=True):
        if not content_filter:
            return True  # a non-existing filter matches every thing
        cache_id = _cache_id("filter-match", content_filter.get("_id") or content_filter.get("name"), article)
        if not cache:
            return self._does_match(content_filter, article, filters, cache)
        elif not hasattr(flask.g, cache_id):
            setattr(flask.g, cache_id, self._does_match(content_filter, article, filters, cache))
        return getattr(flask.g, cache_id)

    def _does_match(self, content_filter, article, filters, cache=True):
        for index, expression in enumerate(content_filter.get("content_filter", [])):
            if not expression.get("expression"):
                raise SuperdeskApiError.badRequestError(
                    _("Filter statement {index} does not have a filter condition").format(index=index + 1)
                )
            if "fc" in expression.get("expression", {}):
                if not self._does_filter_condition_match(content_filter, article, filters, expression, cache):
                    continue
            if "pf" in expression.get("expression", {}):
                if not self._does_content_filter_match(content_filter, article, filters, expression, cache):
                    continue
            return True
        return False

    def _does_filter_condition_match(self, content_filter, article, filters, expression, cache=True) -> bool:
        filter_condition_service = get_resource_service("filter_conditions")
        for f in expression["expression"]["fc"]:
            cache_id = _cache_id("filter-condition-match", f, article)
            if not cache or not hasattr(flask.g, cache_id):
                fc = (
                    filters.get("filter_conditions", {}).get(f, {}).get("fc")
                    if filters
                    else filter_condition_service.get_cached_by_id(f)
                )
                if not fc:
                    logger.error("Missing filter condition %s in content filter %s", f, content_filter.get("name"))
                    return False
                filter_condition = FilterCondition.parse(fc)
                if not cache:
                    return filter_condition.does_match(article)
                setattr(flask.g, cache_id, filter_condition.does_match(article))
            if not getattr(flask.g, cache_id):
                return False
        return True

    def _does_content_filter_match(self, content_filter, article, filters, expression, cache=True) -> bool:
        for f in expression["expression"]["pf"]:
            cache_id = _cache_id("content-filter-match", f, article)
            if not cache or not hasattr(flask.g, cache_id):
                current_filter = (
                    filters.get("content_filters", {}).get(f, {}).get("cf") if filters else self.get_cached_by_id(f)
                )
                if not cache:
                    return self.does_match(current_filter, article, filters=filters)
                setattr(flask.g, cache_id, self.does_match(current_filter, article, filters=filters))
            if not getattr(flask.g, cache_id):
                return False
        return True

    def get_api_blocking_filters(self):
        cached = self.get_cached()
        return [f for f in cached if f.get("api_block")]


def _cache_id(prefix, _id, article) -> str:
    return "-".join([prefix, str(_id), str(article.get("_id") or article.get("guid"))])
