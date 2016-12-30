# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from .commands import CreateUserCommand
from superdesk import get_resource_service
from superdesk.tests import TestCase


class UsersTestCase(TestCase):

    def test_create_user_command(self):
        if not self.app.config.get('LDAP_SERVER'):
            user = {'username': 'foo', 'password': 'bar', 'email': 'baz'}
            cmd = CreateUserCommand()
            cmd.run(user['username'], user['password'], user['email'], admin=True)
            auth_user = get_resource_service('auth_db').authenticate(user)
            self.assertEquals(auth_user['username'], user['username'])

            cmd.run(user['username'], user['password'], user['email'], admin=True)
            auth_user2 = get_resource_service('auth_db').authenticate(user)
            self.assertEquals(auth_user2['username'], user['username'])
            self.assertEquals(auth_user2['_id'], auth_user['_id'])

    def test_create_user_command_no_update(self):
        if not self.app.config.get('LDAP_SERVER'):
            user = {'username': 'foo', 'password': 'bar', 'email': 'baz'}
            cmd = CreateUserCommand()
            cmd.run(
                user['username'], user['password'], user['email'], admin=True
            )
            cmd.run(
                user['username'], "new_password", user['email'], admin=True
            )
            get_resource_service('auth_db').authenticate(user)
