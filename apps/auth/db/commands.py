# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import json
import csv
from pathlib import Path
from base64 import b64encode
from flask import current_app as app
import superdesk
from superdesk.utils import get_hash, is_hashed


logger = logging.getLogger(__name__)
USER_FIELDS_NAMES = {'username', 'email', 'password', 'first_name', 'last_name', 'sign_off', 'role'}


class CreateUserCommand(superdesk.Command):
    """Create a user with given username, password and email.

    If user with given username exists it's noop.

    Example:
    ::

        $ python manage.py users:create -u admin -p admin -e 'admin@example.com' --admin

    """

    option_list = (
        superdesk.Option('--username', '-u', dest='username', required=True),
        superdesk.Option('--password', '-p', dest='password', required=True),
        superdesk.Option('--email', '-e', dest='email', required=True),
        superdesk.Option('--admin', '-a', dest='admin', required=False, action='store_true'),
        superdesk.Option('--support', '-s', dest='support', required=False, action='store_true'),
    )

    def run(self, username, password, email, admin=False, support=False):

        # force type conversion to boolean
        user_type = 'administrator' if admin else 'user'

        userdata = {
            'username': username,
            'password': password,
            'email': email,
            'user_type': user_type,
            'is_active': admin,
            'is_support': support,
            'needs_activation': not admin
        }

        with app.test_request_context('/users', method='POST'):
            if userdata.get('password', None) and not is_hashed(userdata.get('password')):
                userdata['password'] = get_hash(userdata.get('password'),
                                                app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))

            user = superdesk.get_resource_service('users').find_one(username=userdata.get('username'), req=None)

            if user:
                logger.info('user already exists %s' % (userdata))
            else:
                logger.info('creating user %s' % (userdata))
                superdesk.get_resource_service('users').post([userdata])
                logger.info('user saved %s' % (userdata))

            return userdata


class ImportUsersCommand(superdesk.Command):
    """Imports users from JSON or CSV file.

    The file is a list of users, where the fields can be:

        - ``username`` (String), mandatory
          if there is already a user with given username, it will be skipped.
        - ``email`` (String), mandatory
          if there is already a user with given email, it will be skipped.
        - ``password`` (String)
        - ``first_name`` (String)
        - ``last_name`` (String)
        - ``sign_off`` (String)
        - ``role`` (String): name of an existing role to assign.
          The role must exist, otherwise the user will be skipped.
          Note that the role is case sensitive.

    For JSON, it's a list of object, each user must map field name to value.

    For CSV, fields names can be put in the first row of the CSV file.
    If the first row doesn't contain fields names, mapping between columns and fields
    must be done using ``-f`` (fields mut be specified in the same order as columns).

    File extension is used to detect if the file is JSON or CSV.

    Examples:
    ::

        $ python manage.py users:import path/to/users_list.json

        $ python manage.py users:import -f username -f email -f first_name -f last_name path/to/users_list.csv

    or, if the first row of your CSV file contains the fields names::

        $ python manage.py users:import path/to/users_list.csv

    """

    option_list = (
        superdesk.Option('--field', '-f', dest='fields', action='append'),
        superdesk.Option('--activation-email', '-a', dest='activation_email', required=False, action='store_true'),
        superdesk.Option('import_file'),
    )

    def run(self, fields, import_file, activation_email=False):
        import_path = Path(import_file)
        if import_path.suffix == '.csv':
            try:
                with import_path.open(newline='') as f:
                    reader = csv.DictReader(f, fieldnames=fields)
                    data = list(reader)
            except Exception as e:
                self.parser.error(
                    "Can't decode file at {path!r}, are you sure it's valid CSV? Error: {exc_msg}".format(
                        path=import_file, exc_msg=e))
        else:
            # we default to JSON even if the suffix is not ".json", as the parser will fail anyway if it's an other
            # format
            if fields is not None:
                self.parser.error("--field argument can only be used with CSV files")
            try:
                with open(import_file) as f:
                    data = json.load(f)
            except json.JSONDecodeError as e:
                self.parser.error(
                    "Can't decode file at {path!r}, are you sure it's valid JSON? Error: {exc_msg}".format(
                        path=import_file, exc_msg=e))

        if not isinstance(data, list):
            self.parser.error("Invalid data file at {path!r}: import data must be a list of objects".format(
                path=import_file))

        users_service = superdesk.get_resource_service('users')
        roles_service = superdesk.get_resource_service('roles')

        created_users = 0

        for user_data in data:
            if not isinstance(user_data, dict):
                self.parser.error(
                    "Invalid user data when importing {path!r}: user data must be an object, not {data_type}:\ndata: "
                    "{data!r}".format(
                        path=import_file, data_type=type(user_data), data=user_data))

            try:
                username = user_data['username']
                email = user_data['email']
                if not username.strip() or not email.strip():
                    raise KeyError
            except KeyError:
                logger.warning(
                    "Invalid user data when importing {path!r}: \"username\" and \"email\" are mandatory\ndata: "
                    "{data!r}".format(
                        path=import_file, data=user_data))
                continue

            diff_fields = set(user_data) - USER_FIELDS_NAMES
            if diff_fields:
                logger.warning(
                    "Invalid fields found ({invalid_fields}), they will be ignored. "
                    "Valid fields are: {valid_fields}".format(
                        invalid_fields=', '.join(sorted(diff_fields)),
                        valid_fields=', '.join(sorted(USER_FIELDS_NAMES))
                    )
                )

            clean_data = {
                'needs_activation': activation_email
            }
            try:
                for field_name in USER_FIELDS_NAMES.intersection(user_data):
                    value = user_data[field_name]
                    if field_name == 'role':
                        role_data = roles_service.find_one(req=None, name=value)
                        if role_data is None:
                            raise ValueError(
                                "The role {role!r} for user {username!r} is invalid, skipping user\ndata: {data!r}"
                                .format(
                                    role=value,
                                    username=username,
                                    data=data,
                                )
                            )
                        value = role_data['_id']
                    clean_data[field_name] = value

                user_id = users_service.post([clean_data])[0]
            except Exception as e:
                logger.warning("Can't create user {username!r}: {reason}\n{data!r}".format(
                    username=username, reason=e, data=data))
                continue
            logger.info("user {username!r} created with id '{user_id}'".format(
                username=username, user_id=user_id))

            created_users += 1

        print(
            "{created_users}/{len_users} successfully created users".format(
                created_users=created_users,
                len_users=len(data)
            )
        )


class HashUserPasswordsCommand(superdesk.Command):
    """Hash all the user passwords which are not hashed yet.

    Example:
    ::

        $ python manage.py users:hash_passwords

    """

    def run(self):
        users = superdesk.get_resource_service('auth_users').get(req=None, lookup={})
        for user in users:
            pwd = user.get('password')
            if not is_hashed(pwd):
                updates = {}
                hashed = get_hash(user['password'], app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))
                user_id = user.get('_id')
                updates['password'] = hashed
                superdesk.get_resource_service('users').patch(user_id, updates=updates)


class GetAuthTokenCommand(superdesk.Command):
    """Gets auth token.

    Generate an authorization token to be able to authenticate against the REST api without
    starting the client the copy the authorization header.

    Example:
    ::

        $ python manage.py users:get_auth_token --username=admin --password=123123

    """

    option_list = (
        superdesk.Option('--username', '-u', dest='username', required=True),
        superdesk.Option('--password', '-p', dest='password', required=True)
    )

    def run(self, username, password):
        credentials = {
            'username': username,
            'password': password
        }
        service = superdesk.get_resource_service('auth_db')
        id = str(service.post([credentials])[0])
        print('Session ID:', id)
        creds = service.find_one(req=None, _id=id)
        token = creds.get('token').encode('ascii')
        encoded_token = b'basic ' + b64encode(token + b':')
        print('Generated token: ', encoded_token)
        return encoded_token


superdesk.command('users:create', CreateUserCommand())
superdesk.command('users:import', ImportUsersCommand())
superdesk.command('users:hash_passwords', HashUserPasswordsCommand())
superdesk.command('users:get_auth_token', GetAuthTokenCommand())
