# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


from .ninjs_formatter import NINJSFormatter
import superdesk


class NewsroomNinjsFormatter(NINJSFormatter):
    def __init__(self):
        self.format_type = "newsroom ninjs"
        self.can_preview = False
        self.can_export = False
        self.internal_renditions = ["original", "viewImage", "baseImage"]

    def _format_products(self, article):
        """
        Return a list of API product id's that the article matches.

        :param article:
        :return:
        """
        result = superdesk.get_resource_service("product_tests").test_products(article, lookup=None)
        return [{"code": p["product_id"], "name": p.get("name")} for p in result if p.get("matched", False)]

    def _transform_to_ninjs(self, article, subscriber, recursive=True):
        ninjs = super()._transform_to_ninjs(article, subscriber, recursive)

        if article.get("ingest_id") and article.get("auto_publish"):
            ninjs["guid"] = article.get("ingest_id")
            ninjs["version"] = article.get("ingest_version")

        ninjs["products"] = self._format_products(article)

        if article.get("assignment_id"):
            assignment = superdesk.get_resource_service("assignments").find_one(req=None, _id=article["assignment_id"])
            if assignment is not None:
                if assignment.get("coverage_item"):
                    ninjs.setdefault("coverage_id", assignment["coverage_item"])
                if assignment.get("planning_item"):
                    ninjs.setdefault("planning_id", assignment["planning_item"])

        return ninjs
