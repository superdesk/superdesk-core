"""
Superdesk OAuth support

.. versionadded:: 1.9

There is ``oauth`` resource for authenticating users by email.
Email must be provided by trusted identity service, eg. Google.

The authentication flow with js client is:

- Client opens server api url in a new window,.
- There is a redirect to auth provider (eg. Google).
- Once authenticated user is redirected back to server api url.
- There user email from auth provider is used to authenticate user.
- Template is rendered with session data which sends message to parent window and popup is closed.

.. autofunction:: auth_user

"""

import logging
import superdesk

from flask import render_template, current_app as app

from apps.auth.auth import AuthResource
from apps.auth.service import AuthService
from superdesk.validation import ValidationError


RESOURCE = 'oauth'
TEMPLATE = 'oauth_authorized.html'


logger = logging.getLogger(__name__)


class OAuthResource(AuthResource):
    internal_resource = True


class OAuthService(AuthService):

    def authenticate(self, document):
        if not document.get('email'):
            return
        return superdesk.get_resource_service('auth_users').find_one(req=None, email=document['email'].lower())


def auth_user(email, userdata=None):
    """Authenticate user via email.

    This will create new session for user and render template with session data
    which is used by client to setup authentication.

    :param email: user email address
    """
    # we don't get email from service
    if userdata and userdata.get('email'):
        email = userdata['email']
    data = [{'email': email}]
    if not email:
        return render_template(TEMPLATE, data={'error': 404})
    try:
        superdesk.get_resource_service(RESOURCE).post(data)
        data[0]['_id'] = str(data[0]['_id'])
        data[0]['user'] = str(data[0]['user'])
        if userdata:
            superdesk.get_resource_service('users').update_external_user(data[0]['user'], userdata)
        return render_template(TEMPLATE, data=data[0])
    except ValueError:
        if not app.config['USER_EXTERNAL_CREATE'] or not userdata:
            return render_template(TEMPLATE, data={'error': 404})

    # create new user using userdata
    # and re-run auth
    try:
        user = superdesk.get_resource_service('users').create_external_user(userdata)
        return auth_user(user['email'])
    except ValidationError as err:  # can't create user, so let it fail on next iteration
        logger.error('can not create user automaticaly, userdata is not valid', extra={
            'userdata': userdata,
            'errors': err,
        })

    return auth_user(None)


def init_app(app):
    superdesk.register_resource(RESOURCE, OAuthResource, OAuthService, _app=app)
