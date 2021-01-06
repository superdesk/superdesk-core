# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from nose.tools import raises
from superdesk.tests import TestCase
from superdesk.privilege import privilege, get_privilege_list, _privileges


class PrivilegeTestCase(TestCase):
    def setUp(self):
        _privileges_saved = _privileges.copy()
        _privileges.clear()

        def revert():
            _privileges.clear()
            _privileges.update(_privileges_saved)

        self.addCleanup(revert)

    def test_privilege_registration(self):
        _privileges.clear()

        privilege(name="ingest", label="Ingest")
        privilege(name="archive", label="Archive")

        self.assertIn("ingest", _privileges)
        self.assertIn("archive", _privileges)

        self.assertEqual(2, len(get_privilege_list()))

    @raises(Exception)
    def test_privilege_name_has_no_dots(self):
        privilege(name="test.")
