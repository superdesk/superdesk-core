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

import click

from superdesk.core import get_app_config
from superdesk.commands import cli
from superdesk.errors import SuperdeskApiError
import superdesk
from .ldap import ADAuth, add_default_values, get_user_query

logger = logging.getLogger(__name__)


@cli.command("users:copyfromad")
@click.option("--ad_username", "-adu", required=True)
@click.option("--ad_password", "-adp", required=True)
@click.option("--username_to_import", "-u", "username", required=True)
@click.option("--admin", "-a", required=False)
async def cli_users_copyfromad(ad_username, ad_password, username, admin):
    """Responsible for importing a user profile from Active Directory (AD) to Mongo.

    This command runs on assumption that the user executing this command and
    the user whose profile need to be imported need not to be the same. Uses ad_username and ad_password to bind to AD
    and then searches for a user identified by username_to_import and if found imports into Mongo.

    Example:
    ::

        $ python manage.py users:copyfromad --ad_username=ad_uname --ad_password=123 --username_to_import=admin

    """

    await ImportUserProfileFromADCommand().run(ad_username, ad_password, username, admin)


class ImportUserProfileFromADCommand:
    async def run(self, ad_username, ad_password, username, admin="false"):
        """Imports or Updates a User Profile from AD to Mongo.

        :param ad_username: Active Directory Username
        :param ad_password: Password of Active Directory Username
        :param username: Username as in Active Directory whose profile needs to be imported to Superdesk.
        :return: User Profile.
        """

        # force type conversion to boolean
        user_type = "administrator" if admin is not None and admin.lower() == "true" else "user"

        # Authenticate and fetch profile from AD
        ad_auth = ADAuth(
            get_app_config("LDAP_SERVER"),
            get_app_config("LDAP_SERVER_PORT"),
            get_app_config("LDAP_BASE_FILTER"),
            get_app_config("LDAP_USER_FILTER"),
            get_app_config("LDAP_USER_ATTRIBUTES"),
            get_app_config("LDAP_FQDN"),
        )

        user_data = ad_auth.authenticate_and_fetch_profile(ad_username, ad_password, username)
        print(user_data)

        if len(user_data) == 0:
            raise SuperdeskApiError.notFoundError("Username not found")

        # Check if User Profile already exists in Mongo
        users_service = superdesk.get_resource_service("users")
        user = await users_service.find_one_async(req=None, **get_user_query(username))

        if user:
            await users_service.patch_async(user.get("_id"), user_data)
        else:
            add_default_values(user_data, username, user_type=user_type)
            await users_service.post_async([user_data])

        print(user_data)
        return user_data
