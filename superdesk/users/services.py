# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import flask
import logging
from bson import ObjectId
from flask import current_app as app
from eve.utils import config
from superdesk.activity import add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE
from superdesk.metadata.item import SIGN_OFF
from superdesk.services import BaseService
from superdesk.utils import is_hashed, get_hash, compare_preferences
from superdesk import get_resource_service
from superdesk.emails import send_user_status_changed_email, send_activate_account_email
from superdesk.utc import utcnow
from superdesk.privilege import get_privilege_list
from superdesk.errors import SuperdeskApiError
from superdesk.users.errors import UserInactiveError, UserNotRegisteredException
from superdesk.notification import push_notification

logger = logging.getLogger(__name__)


def get_display_name(user):
    if user.get('first_name') or user.get('last_name'):
        display_name = '%s %s' % (user.get('first_name', ''), user.get('last_name', ''))
        return display_name.strip()
    else:
        return user.get('username')


def is_admin(user):
    """Test if given user is admin.

    :param user
    """
    return user.get('user_type', 'user') == 'administrator'


def get_admin_privileges():
    """Get privileges for admin user."""
    return dict.fromkeys([p['name'] for p in get_privilege_list()], 1)


def get_privileges(user, role):
    """Get privileges for given user and role.

    :param user
    :param role
    """
    if is_admin(user):
        return get_admin_privileges()

    if role:
        role_privileges = role.get('privileges', {})
        return dict(
            list(role_privileges.items()) + list(user.get('privileges', {}).items())
        )

    return user.get('privileges', {})


def current_user_has_privilege(privilege):
    """Test if current user has given privilege.

    In case there is no current user we assume it's system (via worker/manage.py)
    and let it pass.

    :param privilege
    """
    if not getattr(flask.g, 'user', None):  # no user - worker can do it
        return True
    privileges = get_privileges(flask.g.user, getattr(flask.g, 'role', None))
    return privileges.get(privilege, False)


def is_sensitive_update(updates):
    """Test if given update is sensitive and might change user privileges."""
    return 'role' in updates or 'privileges' in updates or 'user_type' in updates


def get_invisible_stages(user_id):
    user_desks = list(get_resource_service('user_desks').get(req=None, lookup={'user_id': user_id}))
    user_desk_ids = [d['_id'] for d in user_desks]
    return get_resource_service('stages').get_stages_by_visibility(False, user_desk_ids)


def set_sign_off(user):
    """
    Set sign_off property on user if it's not set already.
    """

    if SIGN_OFF not in user:
        signOffMapping = app.config.get('SIGN_OFF_MAPPING', None)
        if signOffMapping and signOffMapping in user:
            user[SIGN_OFF] = user[signOffMapping]
        elif 'first_name' not in user or 'last_name' not in user:
            user[SIGN_OFF] = user['username'][:3].upper()
        else:
            user[SIGN_OFF] = '{first_name[0]}{last_name[0]}'.format(**user)


def get_sign_off(user):
    """
    Gets sign_off property on user if it's not set already.
    """

    if SIGN_OFF not in user:
        set_sign_off(user)

    return user[SIGN_OFF]


class UsersService(BaseService):

    def __is_invalid_operation(self, user, updates, method):
        """Checks if the requested 'PATCH' or 'DELETE' operation is Invalid.

        Operation is invalid if one of the below is True:
            1. Check if the user is updating his/her own status.
            2. Check if the user is changing the role/user_type/privileges of other logged-in users.
            3. A user without 'User Management' privilege is changing status/role/user_type/privileges

        :return: error message if invalid.
        """

        if 'user' in flask.g:
            if method == 'PATCH':
                if 'is_active' in updates or 'is_enabled' in updates:
                    if str(user['_id']) == str(flask.g.user['_id']):
                        return 'Not allowed to change your own status'
                    elif not current_user_has_privilege('users'):
                        return 'Insufficient privileges to change user state'
                if str(user['_id']) != str(flask.g.user['_id']) and user.get('session_preferences') \
                        and is_sensitive_update(updates):
                    return 'Not allowed to change the role/user_type/privileges of a logged-in user'
            elif method == 'DELETE' and str(user['_id']) == str(flask.g.user['_id']):
                return 'Not allowed to disable your own profile.'

        if method == 'PATCH' and is_sensitive_update(updates) and not current_user_has_privilege('users'):
            return 'Insufficient privileges to update role/user_type/privileges'

    def __handle_status_changed(self, updates, user):
        enabled = updates.get('is_enabled', None)
        active = updates.get('is_active', None)

        if enabled is not None or active is not None:
            get_resource_service('auth').delete_action({'username': user.get('username')})  # remove active tokens
            updates['session_preferences'] = {}

            # send email notification
            can_send_mail = get_resource_service('preferences').email_notification_is_enabled(user_id=user['_id'])

            status = ''

            if enabled is not None:
                status = 'enabled' if enabled else 'disabled'

            if (status == '' or status == 'enabled') and active is not None:
                status = 'enabled and active' if active else 'enabled but inactive'

            if can_send_mail:
                send_user_status_changed_email([user.get('email')], status)

    def __send_notification(self, updates, user):
        user_id = user['_id']

        if 'is_enabled' in updates and not updates['is_enabled']:
            push_notification('user_disabled', updated=1, user_id=str(user_id))
        elif 'is_active' in updates and not updates['is_active']:
            push_notification('user_inactivated', updated=1, user_id=str(user_id))
        elif 'role' in updates:
            push_notification('user_role_changed', updated=1, user_id=str(user_id))
        elif 'privileges' in updates:
            added, removed, modified = compare_preferences(user.get('privileges', {}), updates['privileges'])
            if len(removed) > 0 or (1, 0) in modified.values():
                push_notification('user_privileges_revoked', updated=1, user_id=str(user_id))
            if len(added) > 0:
                add_activity(ACTIVITY_UPDATE,
                             'user {{user}} has been granted new privileges: Please re-login.',
                             self.datasource,
                             notify=[user_id],
                             user=user.get('display_name', user.get('username')))
        elif 'user_type' in updates:
            if not is_admin(updates):
                push_notification('user_type_changed', updated=1, user_id=str(user_id))
            else:
                add_activity(ACTIVITY_UPDATE,
                             'user {{user}} is updated to administrator: Please re-login.',
                             self.datasource,
                             notify=[user_id],
                             user=user.get('display_name', user.get('username')))
        else:
            push_notification('user', updated=1, user_id=str(user_id))

    def get_avatar_renditions(self, doc):
        renditions = get_resource_service('upload').find_one(req=None, _id=doc)
        return renditions.get('renditions') if renditions is not None else None

    def on_create(self, docs):
        for user_doc in docs:
            user_doc.setdefault('display_name', get_display_name(user_doc))
            user_doc.setdefault(SIGN_OFF, set_sign_off(user_doc))
            user_doc.setdefault('role', get_resource_service('roles').get_default_role_id())
            if user_doc.get('avatar'):
                user_doc.setdefault('avatar_renditions', self.get_avatar_renditions(user_doc['avatar']))

            get_resource_service('preferences').set_user_initial_prefs(user_doc)

    def on_created(self, docs):
        for user_doc in docs:
            self.__update_user_defaults(user_doc)
            add_activity(ACTIVITY_CREATE, 'created user {{user}}', self.datasource,
                         user=user_doc.get('display_name', user_doc.get('username')))
            self.update_stage_visibility_for_user(user_doc)

    def on_update(self, updates, original):
        """Overriding the method to:

        1. Prevent user from the below:
            a. Check if the user is updating his/her own status.
            b. Check if the user is changing the status of other logged-in users.
            c. A user without 'User Management' privilege is changing role/user_type/privileges
        2. Set Sign Off property if it's not been set already
        """
        error_message = self.__is_invalid_operation(original, updates, 'PATCH')
        if error_message:
            raise SuperdeskApiError.forbiddenError(message=error_message)

        if updates.get('is_enabled', False):
            updates['is_active'] = True

        if SIGN_OFF not in original:
            set_sign_off(updates)

        if updates.get('avatar'):
            updates['avatar_renditions'] = self.get_avatar_renditions(updates['avatar'])

    def on_updated(self, updates, user):
        if 'role' in updates or 'privileges' in updates:
            get_resource_service('preferences').on_update(updates, user)
        self.__handle_status_changed(updates, user)
        self.__send_notification(updates, user)

    def on_delete(self, user):
        """Overriding the method to prevent user from the below:

        1. Check if the user is updating his/her own status.
        2. Check if the user is changing the status of other logged-in users.
        3. A user without 'User Management' privilege is changing role/user_type/privileges
        """
        updates = {'is_enabled': False, 'is_active': False}
        error_message = self.__is_invalid_operation(user, updates, 'DELETE')
        if error_message:
            raise SuperdeskApiError.forbiddenError(message=error_message)

    def delete(self, lookup):
        """
        Overriding the method to prevent from hard delete
        """

        user = super().find_one(req=None, _id=str(lookup['_id']))
        return super().update(id=lookup['_id'], updates={'is_enabled': False, 'is_active': False}, original=user)

    def __clear_locked_items(self, user_id):
        archive_service = get_resource_service('archive')
        archive_autosave_service = get_resource_service('archive_autosave')

        doc_to_unlock = {'lock_user': None, 'lock_session': None, 'lock_time': None, 'force_unlock': True}
        user = ObjectId(user_id) if isinstance(user_id, str) else user_id
        query = {
            '$or': [{'lock_user': user},
                    {'task.user': user, 'task.desk': {'$exists': False}}]
        }

        items_locked_by_user = archive_service.get_from_mongo(req=None, lookup=query)

        if items_locked_by_user and items_locked_by_user.count():
            for item in items_locked_by_user:
                # delete the item if nothing is saved so far
                if item[config.VERSION] == 0 and item['state'] == 'draft':
                    get_resource_service('archive').delete(lookup={'_id': item['_id']})
                else:
                    archive_service.update(item['_id'], doc_to_unlock, item)
                    archive_autosave_service.delete(lookup={'_id': item['_id']})

    def on_deleted(self, doc):
        """Overriding to add to activity stream and handle user clean up.

        1. Authenticated Sessions
        2. Locked Articles
        3. Reset Password Tokens
        """

        add_activity(ACTIVITY_UPDATE, 'disabled user {{user}}', self.datasource,
                     user=doc.get('display_name', doc.get('username')))
        self.__clear_locked_items(str(doc['_id']))
        self.__handle_status_changed(updates={'is_enabled': False, 'is_active': False}, user=doc)

    def on_fetched(self, document):
        for doc in document['_items']:
            self.__update_user_defaults(doc)

    def on_fetched_item(self, doc):
        self.__update_user_defaults(doc)

    def __update_user_defaults(self, doc):
        """Set default fields for users"""
        doc.pop('password', None)

        doc.setdefault('display_name', get_display_name(doc))
        doc.setdefault('is_enabled', doc.get('is_active'))
        doc.setdefault(SIGN_OFF, set_sign_off(doc))
        doc['dateline_source'] = app.config['ORGANIZATION_NAME_ABBREVIATION']

    def user_is_waiting_activation(self, doc):
        return doc.get('needs_activation', False)

    def is_user_active(self, doc):
        return doc.get('is_active', False)

    def get_role(self, user):
        if user:
            role_id = user.get('role', None)
            if role_id:
                return get_resource_service('roles').find_one(_id=role_id, req=None)
        return None

    def set_privileges(self, user, role):
        user['active_privileges'] = get_privileges(user, role)

    def get_users_by_user_type(self, user_type='user'):
        return list(self.get(req=None, lookup={'user_type': user_type}))

    def get_users_by_role(self, role_id):
        return list(self.get(req=None, lookup={'role': role_id}))

    def get_invisible_stages(self, user_id):
        return get_invisible_stages(user_id) if user_id else []

    def get_invisible_stages_ids(self, user_id):
        return [str(stage['_id']) for stage in self.get_invisible_stages(user_id)]

    def get_user_by_email(self, email_address):
        """Finds a user by the given email_address.

        Does a exact match.

        :param email_address:
        :type email_address: str with valid email format
        :return: user object if found.
        :rtype: dict having user details :py:class: `superdesk.users.users.UsersResource`
        :raises: UserNotRegisteredException if no user found with the given email address.
        """
        user = self.find_one(req=None, email=email_address)
        if not user:
            raise UserNotRegisteredException('No user registered with email %s' % email_address)

        return user

    def update_stage_visibility_for_users(self):
        logger.info('Updating Stage Visibility Started')
        users = list(get_resource_service('users').get(req=None, lookup=None))
        for user in users:
            self.update_stage_visibility_for_user(user)

        logger.info('Updating Stage Visibility Completed')

    def update_stage_visibility_for_user(self, user):
        try:
            logger.info('Updating Stage Visibility for user {}.'.format(user.get(config.ID_FIELD)))
            stages = self.get_invisible_stages_ids(user.get(config.ID_FIELD))
            self.system_update(user.get(config.ID_FIELD), {'invisible_stages': stages}, user)
            user['invisible_stages'] = stages
            logger.info('Updated Stage Visibility for user {}.'.format(user.get(config.ID_FIELD)))
        except:
            logger.exception('Failed to update the stage visibility '
                             'for user: {}'.format(user.get(config.ID_FIELD)))


class DBUsersService(UsersService):
    """
    Service class for UsersResource and should be used when AD is inactive.
    """

    def on_create(self, docs):
        super().on_create(docs)
        for doc in docs:
            if doc.get('password', None) and not is_hashed(doc.get('password')):
                doc['password'] = get_hash(doc.get('password'), app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12))

    def on_created(self, docs):
        """Send email to user with reset password token."""
        super().on_created(docs)
        resetService = get_resource_service('reset_user_password')
        activate_ttl = app.config['ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE']
        for doc in docs:
            if self.user_is_waiting_activation(doc):
                tokenDoc = {'user': doc['_id'], 'email': doc['email']}
                id = resetService.store_reset_password_token(tokenDoc, doc['email'], activate_ttl, doc['_id'])
                if not id:
                    raise SuperdeskApiError.internalError('Failed to send account activation email.')
                tokenDoc.update({'username': doc['username']})
                send_activate_account_email(tokenDoc)

    def on_update(self, updates, user):
        super().on_update(updates, user)
        if updates.get('first_name') or updates.get('last_name'):
            updated_user = {'first_name': user.get('first_name', ''),
                            'last_name': user.get('last_name', ''),
                            'username': user.get('username', '')}
            if updates.get('first_name'):
                updated_user['first_name'] = updates.get('first_name')
            if updates.get('last_name'):
                updated_user['last_name'] = updates.get('last_name')
            updates['display_name'] = get_display_name(updated_user)

    def update_password(self, user_id, password):
        """Update the user password.

        Returns true if successful.
        """
        user = self.find_one(req=None, _id=user_id)

        if not user:
            raise SuperdeskApiError.unauthorizedError('User not found')

        if not self.is_user_active(user):
            raise UserInactiveError()

        updates = {'password': get_hash(password, app.config.get('BCRYPT_GENSALT_WORK_FACTOR', 12)),
                   app.config['LAST_UPDATED']: utcnow()}

        if self.user_is_waiting_activation(user):
            updates['needs_activation'] = False

        self.patch(user_id, updates=updates)

    def on_deleted(self, doc):
        """
        Overriding clean up reset password tokens:
        """

        super().on_deleted(doc)
        get_resource_service('reset_user_password').remove_all_tokens_for_email(doc.get('email'))
