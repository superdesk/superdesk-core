# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from datetime import datetime, timedelta

from flask import current_app as app

import superdesk


class DictObject:
    def __init__(self, **args):
        self.__dict__.update(args)


class AuthDataManager:

    @staticmethod
    def get_client(client_id):
        """Loads a client from the database and returns it as an object or None.
        """
        client = superdesk.get_resource_service('clients').find_one(req=None, _id=client_id)
        if not client:
            return None
        client['client_id'] = client['_id']
        client['default_scopes'] = app.config['OAUTH2_SCOPES']
        client['default_redirect_uri'] = app.config['CONTENTAPI_URL']
        return DictObject(**client)

    @staticmethod
    def get_user(username, password, *args, **kwargs):
        """Loads a user from the database and returns it as an object or None.
        """
        user_service = superdesk.get_resource_service('users')
        user = user_service.find_one(req=None, username=username) or {}
        user_password = user.get('password', '').encode('UTF-8')
        user = user if user_service.password_match(password.encode('UTF-8'), user_password) else {}
        user = DictObject(**user)
        return user if getattr(user, 'username', None) else None

    @staticmethod
    def get_token(access_token=None, refresh_token=None):
        """Loads a token from the database and returns it as an object or None.
        """
        if not (access_token or refresh_token):
            return None

        if access_token:
            token = superdesk.get_resource_service('tokens').find_one(req=None, access_token=access_token)
        elif refresh_token:
            token = superdesk.get_resource_service('tokens').find_one(req=None, refresh_token=refresh_token)
        return DictObject(token)

    @staticmethod
    def save_token(token, request, *args, **kwargs):
        """Saves a token to the database
        """
        client_id = request.client.client_id
        user_id = request.user._id

        # Make sure there is only one grant token for every (client, user)
        old_tokens = superdesk.get_resource_service('tokens').get(req=None,
                                                                  lookup={'client': client_id, 'user': user_id})
        for old_token in old_tokens:
            app.redis.delete(old_token['access_token'])
        superdesk.get_resource_service('tokens').delete({'client': client_id, 'user': user_id})

        expires_in = token.pop('expires_in')
        expires = datetime.utcnow() + timedelta(seconds=expires_in)

        token = {
            'client': request.client.client_id,
            'user': user_id,
            'token_type': token['token_type'],
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'expires': expires
        }
        superdesk.get_resource_service('tokens').post([token])

        # Add the access token to the Redis cache and set it to
        # expire at the appropriate time.
        app.redis.set(token['access_token'], user_id)
        app.redis.expire(token['access_token'], expires_in)
