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
from flask_babel import _

from superdesk import get_resource_service, app
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError


class ContentFilterTestResource(Resource):
    endpoint_name = "content_filter_tests"
    schema = {
        "filter_id": {"type": "string"},
        "article_id": {"type": "string"},
        "return_matching": {"type": "boolean"},
        "filter": {"type": "dict"},
        "match_results": {"type": "list"},
    }
    url = "content_filters/test"
    resource_methods = ["POST"]
    item_methods = []
    resource_title = endpoint_name
    privileges = {"POST": "content_filters"}


class ContentFilterTestService(BaseService):
    def create(self, docs, **kwargs):
        service = get_resource_service("content_filters")
        for doc in docs:
            filter_id = doc.get("filter_id")
            if filter_id:
                content_filter = service.find_one(req=None, _id=filter_id)
            else:
                content_filter = doc.get("filter")

            if not content_filter:
                raise SuperdeskApiError.badRequestError(_("Content filter not found"))

            if "article_id" in doc:
                article_id = doc.get("article_id")
                article = get_resource_service("archive").find_one(req=None, _id=article_id)
                if not article and "planning" in app.config.get("INSTALLED_APPS", []):
                    article = get_resource_service("planning").find_one(None, _id=article_id)
                if not article:
                    article = get_resource_service("ingest").find_one(req=None, _id=article_id)
                    if not article:
                        raise SuperdeskApiError.badRequestError(_("Article not found!"))
                try:
                    doc["match_results"] = service.does_match(content_filter, article)
                except Exception as ex:
                    raise SuperdeskApiError.badRequestError(
                        _("Error in testing article: {error}").format(error=str(ex))
                    )
            else:
                try:
                    if doc.get("return_matching", True):
                        query = service.build_elastic_query(content_filter)
                    else:
                        query = service.build_elastic_not_filter(content_filter)
                    query["sort"] = [{"versioncreated": "desc"}]
                    query["size"] = 200
                    req = ParsedRequest()
                    req.args = {"source": json.dumps(query)}
                    doc["match_results"] = list(get_resource_service("archive").get(req=req, lookup=None))
                except Exception as ex:
                    raise SuperdeskApiError.badRequestError(
                        _("Error in testing archive: {error}").format(error=str(ex))
                    )

        return [len(docs)]
