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
from unittest.mock import patch
from superdesk import get_backend
from superdesk.utc import utcnow
from superdesk.tests import TestCase
from apps.auth.db.reset_password import ResetPasswordService


class UserTokenTestCase(TestCase):

    def setUp(self):
        self.service = ResetPasswordService('tokens', backend=get_backend())

    @patch('apps.auth.db.reset_password.get_random_string', return_value='random')
    def test_store_token(self, get_random_string):
        now = utcnow()
        doc = {'user': 'foo', 'email': 'foo@example.com', '_id': 'foo'}
        with patch.object(self.service.backend, 'create') as create:
            with patch('apps.auth.db.reset_password.utcnow', return_value=now):
                self.service.store_reset_password_token(doc, doc['email'], 10, doc['_id'])
            create.assert_called_with('tokens', [{
                'user': 'foo',
                'email': 'foo@example.com',
                '_id': 'foo',
                '_created': now,
                '_updated': now,
                'expire_time': now + timedelta(days=10),
                'token': 'random',
            }])
