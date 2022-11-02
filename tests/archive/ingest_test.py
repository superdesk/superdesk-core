# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import json
import superdesk
from superdesk.tests import TestCase
from werkzeug.datastructures import ImmutableMultiDict
from eve.utils import ParsedRequest


class IngestServiceTests(TestCase):
    def test_highlight_query(self):
        source_query = {
            "query": {
                "filtered": {"query": {"query_string": {"query": "TEST", "lenient": True, "default_operator": "AND"}}}
            }
        }

        req = ParsedRequest()
        req.args = {"source": json.dumps(source_query)}
        req.args = ImmutableMultiDict(req.args)

        archive_service = superdesk.get_resource_service("ingest")
        req = archive_service._get_highlight_query(req)

        args = getattr(req, "args", {})
        source = json.loads(args.get("source")) if args.get("source") else {"query": {"filtered": {}}}

        self.assertEqual(len(source), 2)
        self.assertIn("query", source)
        self.assertIn("highlight", source)
        self.assertIn("fields", source["highlight"])
        self.assertEqual(
            ["body_html", "body_footer", "headline", "slugline", "abstract"], list(source["highlight"]["fields"].keys())
        )
