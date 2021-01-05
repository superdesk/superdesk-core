# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import timedelta
from unittest.mock import patch, ANY
from superdesk.tests import TestCase
from superdesk import get_backend
from superdesk.utc import utcnow


class BackendTestCase(TestCase):
    def test_update_change_etag(self):
        backend = get_backend()
        updates = {"name": "foo"}
        item = {"name": "bar"}
        with self.app.app_context():
            ids = backend.create("ingest", [item])
            doc_old = backend.find_one("ingest", None, _id=ids[0])
            backend.update("ingest", ids[0], updates, doc_old)
            doc_new = backend.find_one("ingest", None, _id=ids[0])
            self.assertNotEqual(doc_old[self.app.config["ETAG"]], doc_new[self.app.config["ETAG"]])

    def test_check_default_dates_on_create(self):
        backend = get_backend()
        item = {"name": "foo"}
        with self.app.app_context():
            ids = backend.create("ingest", [item])
            doc = backend.find_one("ingest", None, _id=ids[0])
            self.assertIn(self.app.config["DATE_CREATED"], doc)
            self.assertIn(self.app.config["LAST_UPDATED"], doc)

    def test_check_default_dates_on_update(self):
        backend = get_backend()
        past = (utcnow() + timedelta(seconds=-2)).replace(microsecond=0)
        item = {"name": "foo", self.app.config["DATE_CREATED"]: past, self.app.config["LAST_UPDATED"]: past}
        updates = {"name": "bar"}
        with self.app.app_context():
            ids = backend.create("ingest", [item])
            doc_old = backend.find_one("ingest", None, _id=ids[0])
            backend.update("ingest", ids[0], updates, doc_old)
            doc_new = backend.find_one("ingest", None, _id=ids[0])
            date1 = doc_old[self.app.config["LAST_UPDATED"]]
            date2 = doc_new[self.app.config["LAST_UPDATED"]]
            self.assertGreaterEqual(date2, date1)
            date1 = doc_old[self.app.config["DATE_CREATED"]]
            date2 = doc_new[self.app.config["DATE_CREATED"]]
            self.assertEqual(date1, date2)

    @patch("superdesk.eve_backend.push_notification")
    def test_update_resource_push_notification(self, push_notification_mock):
        backend = get_backend()
        with self.app.app_context():
            backend.create("archive", [{"_id": "some-id"}])
            push_notification_mock.assert_called_once_with(
                "resource:created",
                resource="archive",
                _id="some-id",
            )

            backend.update(
                "archive",
                "some-id",
                {
                    "foo": 1,
                    "new": {"baz": 1},
                    "same": {"x": "y"},
                    "different": {
                        "same": 1,
                        "foo": 1,
                        "bar": {
                            "baz": 1,
                        },
                    },
                },
                {
                    "baz": 0,
                    "same": {"x": "y"},
                    "different": {
                        "same": 1,
                        "foo": 2,
                        "bar": {
                            "baz": 2,
                        },
                        "missing": 1,
                    },
                },
            )

            push_notification_mock.assert_called_with(
                "resource:updated",
                resource="archive",
                _id="some-id",
                fields={
                    "foo": 1,
                    "new": 1,
                    "new.baz": 1,
                    "different": 1,
                    "different.foo": 1,
                    "different.bar": 1,
                    "different.missing": 1,
                },
            )

            backend.delete("archive", {"_id": "some-id"})
            push_notification_mock.assert_called_with(
                "resource:deleted",
                resource="archive",
                _id="some-id",
            )
