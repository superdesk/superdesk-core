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
from typing import Any
from bson import ObjectId

from superdesk.core.types.search import SearchRequest
from superdesk.resource_fields import VERSION, LAST_UPDATED
from superdesk.core import get_app_config
from superdesk.flask import g
from superdesk.activity import add_activity, ACTIVITY_CREATE, ACTIVITY_UPDATE
from superdesk.metadata.item import SIGN_OFF
from superdesk.core.resources import AsyncResourceService
from superdesk.utils import is_hashed, get_hash, compare_preferences
from superdesk import get_resource_service
from superdesk.emails import send_user_status_changed_email, send_activate_account_email, send_user_type_changed_email
from superdesk.utc import utcnow
from superdesk.privilege import get_item_privilege_name, get_privilege_list
from superdesk.errors import SuperdeskApiError
from superdesk.users.errors import UserInactiveError, UserNotRegisteredException
from superdesk.notification import push_notification
from superdesk.types import UsersResourceModel

from .services import get_invisible_stages_async

logger = logging.getLogger(__name__)


def get_display_name(user: dict | UsersResourceModel):
    if isinstance(user, UsersResourceModel):
        user = user.to_dict()
    if user.get("first_name") or user.get("last_name"):
        display_name = "%s %s" % (user.get("first_name", ""), user.get("last_name", ""))
        return display_name.strip()
    else:
        return user.get("username")


def is_admin(user):
    """Test if given user is admin.

    :param user
    """
    return user.get("user_type", "user") == "administrator"


def get_admin_privileges():
    """Get privileges for admin user."""
    return dict.fromkeys([p["name"] for p in get_privilege_list()], 1)


def get_privileges(user, role):
    """Get privileges for given user and role.

    :param user
    :param role
    """
    if is_admin(user):
        return get_admin_privileges()

    if role:
        role_privileges = role.get("privileges", {})
        return dict(list(role_privileges.items()) + list(user.get("privileges", {}).items()))

    return user.get("privileges", {})


def current_user_has_privilege(privilege):
    """Test if current user has given privilege.

    In case there is no current user we assume it's system (via worker/manage.py)
    and let it pass.

    :param privilege
    """
    if not getattr(g, "user", None):  # no user - worker can do it
        return True
    privileges = get_privileges(g.user, getattr(g, "role", None))
    return privileges.get(privilege, False)


def current_user_has_item_privilege(resource: str, item):
    """Check if current user has privilege for item."""
    return current_user_has_privilege(get_item_privilege_name(resource, item))


def is_sensitive_update(updates):
    """Test if given update is sensitive and might change user privileges."""
    return "role" in updates or "privileges" in updates or "user_type" in updates


def set_sign_off(user: dict | UsersResourceModel):
    """
    Set sign_off property on user if it's not set already.
    """

    current_sign_off = getattr(user, SIGN_OFF, None)
    if current_sign_off is None:
        sign_off_mapping = get_app_config("SIGN_OFF_MAPPING", None)
        if sign_off_mapping and hasattr(user, sign_off_mapping):
            setattr(user, SIGN_OFF, getattr(user, sign_off_mapping))
        elif hasattr(user, SIGN_OFF):
            setattr(user, SIGN_OFF, "")
        elif not hasattr(user, "first_name") or not hasattr(user, "last_name"):
            setattr(user, SIGN_OFF, getattr(user, "username", "")[:3].upper())
        else:
            first_name = getattr(user, "first_name", "")
            sign_off_value = ""
            if first_name:
                sign_off_value = first_name[0]

            last_name = getattr(user, "last_name", "")
            if last_name:
                sign_off_value += last_name[0]
            setattr(user, SIGN_OFF, sign_off_value)


def update_sign_off(updates):
    """
    Update sign_off property on user if the mapped field is changed.
    """

    sign_off_mapping = get_app_config("SIGN_OFF_MAPPING", None)
    if sign_off_mapping and sign_off_mapping in updates:
        updates[SIGN_OFF] = updates[sign_off_mapping]


def get_sign_off(user):
    """
    Gets sign_off property on user if it's not set already.
    """

    if not getattr(user, SIGN_OFF, None):
        set_sign_off(user)

    return getattr(user, SIGN_OFF, None)


class UsersAsyncService(AsyncResourceService[UsersResourceModel]):
    _updating_stage_visibility = True

    async def __handle_status_changed(self, updates: dict[str, Any], user: UsersResourceModel):
        enabled = updates.get("is_enabled", None)
        active = updates.get("is_active", None)

        if enabled is not None or active is not None:
            get_resource_service("auth").delete_action(
                {"username": user.to_dict().get("username")}
            )  # remove active tokens
            updates["session_preferences"] = {}

            # send email notification
            can_send_mail = await get_resource_service("preferences").email_notification_is_enabled_async(
                user_id=user.to_dict().get("_id")
            )

            status = ""

            if enabled is not None:
                status = "enabled" if enabled else "disabled"

            if (status == "" or status == "enabled") and active is not None:
                status = "enabled and active" if active else "enabled but inactive"

            if can_send_mail:
                await send_user_status_changed_email([user.to_dict().get("email")], status)

    async def __send_notification(self, updates: dict[str, Any], user: UsersResourceModel):
        user_id = user.to_dict().get("_id")

        if "is_enabled" in updates and not updates["is_enabled"]:
            push_notification("user_disabled", updated=1, user_id=str(user_id))
        elif "is_active" in updates and not updates["is_active"]:
            push_notification("user_inactivated", updated=1, user_id=str(user_id))
        elif "role" in updates:
            push_notification("user_role_changed", updated=1, user_id=str(user_id))
        elif "privileges" in updates:
            added, removed, modified = compare_preferences(user.to_dict().get("privileges", {}), updates["privileges"])
            if len(removed) > 0 or (1, 0) in modified.values():
                push_notification("user_privileges_revoked", updated=1, user_id=str(user_id))
            if len(added) > 0:
                add_activity(
                    ACTIVITY_UPDATE,
                    "user {{user}} has been granted new privileges: Please re-login.",
                    self.resource_name,
                    notify=[user_id],
                    user=user.to_dict().get("display_name", user.to_dict().get("username")),
                )
        elif "user_type" in updates:
            if not is_admin(updates):
                push_notification("user_type_changed", updated=1, user_id=str(user_id))
            else:
                add_activity(
                    ACTIVITY_UPDATE,
                    "user {{user}} is updated to administrator: Please re-login.",
                    self.resource_name,
                    notify=[user_id],
                    user=user.to_dict().get("display_name", user.to_dict().get("username")),
                )
        else:
            push_notification("user", updated=1, user_id=str(user_id))

    async def get_avatar_renditions(self, doc):
        renditions = get_resource_service("upload").find_one(req=None, _id=doc)
        return renditions.get("renditions") if renditions is not None else None

    async def handle_user_type_changed(self, updates: dict[str, Any], user: UsersResourceModel):
        user_type = updates.get("user_type", None)

        if user_type is not None and user_type == "external":
            can_send_mail = await get_resource_service("preferences").email_notification_is_enabled_async(
                user_id=user.to_dict().get("_id")
            )
            if can_send_mail:
                await send_user_type_changed_email([user.to_dict().get("email")])

    async def on_create(self, docs: list[UsersResourceModel]) -> None:
        for doc in docs:
            if not doc.password_changed_on:
                doc.password_changed_on = utcnow()
            if not doc.display_name:
                doc.display_name = get_display_name(doc)
            if not doc.sign_off:
                set_sign_off(doc)
            if not doc.role:
                doc.role = await get_resource_service("roles").get_default_role_id_async()
            if doc.avatar:
                doc.avatar_renditions = self.get_avatar_renditions(doc.avatar)

            get_resource_service("preferences").set_user_initial_prefs(doc)

    async def on_created(self, docs: list[UsersResourceModel]) -> None:
        for doc in docs:
            await self.__update_user_defaults(doc)
            add_activity(
                ACTIVITY_CREATE,
                "created user {{user}}",
                self.resource_name,
                user=doc.display_name or doc.username or doc.email,
            )
            await self.update_stage_visibility_for_user(doc)

    async def on_update(self, updates: dict[str, Any], original: UsersResourceModel) -> None:
        """Overriding the method to:

        1. Prevent user from the below:
            a. Check if the user is updating his/her own status.
            b. Check if the user is changing the status of other logged-in users.
            c. A user without 'User Management' privilege is changing role/user_type/privileges
        2. Set Sign Off property if it's not been set already
        """
        if updates.get("is_enabled", False):
            updates["is_active"] = True

        update_sign_off(updates)

        if updates.get("avatar"):
            updates["avatar_renditions"] = await self.get_avatar_renditions(updates["avatar"])

    async def on_updated(self, updates: dict[str, Any], original: UsersResourceModel) -> None:
        if "role" in updates or "privileges" in updates:
            await get_resource_service("preferences").on_update_async(updates, original.to_dict())
        await self.__handle_status_changed(updates, original)
        await self.handle_user_type_changed(updates, original)
        await self.__send_notification(updates, original)

    async def on_delete(self, doc: UsersResourceModel):
        """Overriding the method to prevent user from the below:

        1. Check if the user is updating his/her own status.
        2. Check if the user is changing the status of other logged-in users.
        3. A user without 'User Management' privilege is changing role/user_type/privileges
        """
        updates = {"is_enabled": False, "is_active": False}

    async def delete(self, doc: UsersResourceModel, etag: str | None = None):
        """
        Overriding the method to prevent from hard delete
        """
        return await super().update(
            item_id=ObjectId(doc.to_dict().get("_id")), updates={"is_enabled": False, "is_active": False}, etag=etag
        )

    async def __clear_locked_items(self, user_id: str):
        archive_service = get_resource_service("archive")
        archive_autosave_service = get_resource_service("archive_autosave")

        doc_to_unlock = {
            "lock_user": None,
            "lock_session": None,
            "lock_time": None,
            "lock_action": None,
            "force_unlock": True,
        }
        user = ObjectId(user_id) if isinstance(user_id, str) else user_id
        query = {"$or": [{"lock_user": user}, {"task.user": user, "task.desk": {"$exists": False}}]}

        items_locked_by_user = archive_service.get_from_mongo(req=None, lookup=query)

        if items_locked_by_user and items_locked_by_user.count():
            for item in items_locked_by_user:
                # delete the item if nothing is saved so far
                if item[VERSION] == 0 and item["state"] == "draft":
                    get_resource_service("archive").delete(lookup={"_id": item["_id"]})
                else:
                    archive_service.update(item["_id"], doc_to_unlock, item)
                    archive_autosave_service.delete(lookup={"_id": item["_id"]})

    async def on_deleted(self, doc: UsersResourceModel):
        """Overriding to add to activity stream and handle user clean up.

        1. Authenticated Sessions
        2. Locked Articles
        3. Reset Password Tokens
        """

        add_activity(
            ACTIVITY_UPDATE,
            "disabled user {{user}}",
            self.resource_name,
            user=doc.to_dict().get("display_name", doc.to_dict().get("username")),
        )
        await self.__clear_locked_items(str(doc.to_dict().get("_id")))
        await self.__handle_status_changed(updates={"is_enabled": False, "is_active": False}, user=doc)

    async def __update_user_defaults(self, doc: UsersResourceModel):
        """Set default fields for users"""
        doc.password = None
        doc.display_name = get_display_name(doc)
        doc.is_enabled = doc.is_active
        if not doc.sign_off:
            set_sign_off(doc)
        doc.dateline_source = get_app_config("ORGANIZATION_NAME_ABBREVIATION")

    def user_is_waiting_activation(self, doc: UsersResourceModel) -> bool:
        return doc.needs_activation is True

    async def is_user_active(self, doc: UsersResourceModel):
        return doc.to_dict().get("is_active", False)

    async def get_role(self, user: UsersResourceModel):
        if user:
            role_id = user.to_dict().get("role", None)
            if role_id:
                return get_resource_service("roles").find_one(_id=role_id, req=None)
        return None

    async def set_privileges(self, user: UsersResourceModel, role):
        user.active_privileges = get_privileges(user, role)

    async def get_invisible_stages_async(self, user_id) -> list:
        return await get_invisible_stages_async(user_id) if user_id else []

    async def get_invisible_stages_ids(self, user_id) -> list:
        return [str(stage["_id"]) for stage in await self.get_invisible_stages_async(user_id)]

    async def get_user_by_email(self, email_address: str) -> UsersResourceModel | None:
        """Finds a user by the given email_address.

        Does a exact match.

        :param email_address:
        :type email_address: str with valid email format
        :return: user object if found.
        :rtype: dict having user details :py:class: `superdesk.users.users.UsersResource`
        :raises: UserNotRegisteredException if no user found with the given email address.
        """
        search_request = SearchRequest(where={"email_address": email_address}, max_results=1)
        user = await self.find_one(search_request)
        if not user:
            raise UserNotRegisteredException("No user registered with email %s" % email_address)

        return user

    async def update_stage_visibility_for_users(self):
        if not self._updating_stage_visibility:
            return
        logger.info("Updating Stage Visibility Started")
        async for user in self.get_all():
            await self.update_stage_visibility_for_user(user)

        logger.info("Updating Stage Visibility Completed")

    async def update_stage_visibility_for_user(self, user: UsersResourceModel):
        if not self._updating_stage_visibility:
            return
        user_id = user.id
        try:
            logger.info("Updating Stage Visibility for user {}.".format(user_id))
            stages = await self.get_invisible_stages_ids(user_id)
            await self.system_update(user_id, {"invisible_stages": stages})
            user.invisible_stages = stages
            logger.info("Updated Stage Visibility for user {}.".format(user_id))
        except Exception:
            logger.exception("Failed to update the stage visibility " "for user: {}".format(user_id))

    def stop_updating_stage_visibility(self):
        if not get_app_config("SUPERDESK_TESTING"):
            raise RuntimeError("Only allowed during testing")
        self._updating_stage_visibility = False

    def start_updating_stage_visibility(self):
        self._updating_stage_visibility = True


class DBUsersAsyncService(UsersAsyncService):
    """
    Async Service class for UsersResource and should be used when AD is inactive.
    """

    async def on_create(self, docs: list[UsersResourceModel]) -> None:
        await super().on_create(docs)
        for doc in docs:
            if doc.password and not is_hashed(doc.password):
                doc.password = get_hash(doc.password, get_app_config("BCRYPT_GENSALT_WORK_FACTOR", 12))

    async def on_created(self, docs: list[UsersResourceModel]) -> None:
        """Send email to user with reset password token."""
        await super().on_created(docs)
        resetService = get_resource_service("reset_user_password")
        activate_ttl = get_app_config("ACTIVATE_ACCOUNT_TOKEN_TIME_TO_LIVE")
        for doc in docs:
            user_dict = doc.to_dict()
            if self.user_is_waiting_activation(doc) and user_dict.get("user_type") != "external":
                user_id = user_dict.get("_id")
                email = user_dict.get("email")
                username = user_dict.get("username")
                tokenDoc = {"user": user_id, "email": email}
                token_id = resetService.store_reset_password_token(tokenDoc, email, activate_ttl, user_id)
                if not token_id:
                    raise SuperdeskApiError.internalError("Failed to send account activation email.")
                tokenDoc.update({"username": username})

                await send_activate_account_email(tokenDoc, activate_ttl)

    async def on_update(self, updates: dict[str, Any], original: UsersResourceModel) -> None:
        await super().on_update(updates, original)
        if updates.get("first_name") or updates.get("last_name"):
            user = original.to_dict()
            updated_user = {
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
                "username": user.get("username", ""),
            }
            if updates.get("first_name"):
                updated_user["first_name"] = updates.get("first_name")
            if updates.get("last_name"):
                updated_user["last_name"] = updates.get("last_name")
            updates["display_name"] = get_display_name(updated_user)

    async def update_password(self, user_id: ObjectId | str, password: str):
        """Update the user password.

        Returns true if successful.
        """
        user = await self.find_by_id(user_id)

        if not user:
            raise SuperdeskApiError.unauthorizedError("User not found")

        if not await self.is_user_active(user):
            raise UserInactiveError()

        updates = {
            "password": get_hash(password, get_app_config("BCRYPT_GENSALT_WORK_FACTOR", 12)),
            "password_changed_on": utcnow(),
            LAST_UPDATED: utcnow(),
        }

        if self.user_is_waiting_activation(user):
            updates["needs_activation"] = False

        await self.update(user_id, updates=updates)

    async def on_delete(self, doc: UsersResourceModel) -> None:
        """
        Overriding clean up reset password tokens:
        """

        await super().on_deleted(doc)
        get_resource_service("reset_user_password").remove_all_tokens_for_email(doc.to_dict().get("email"))
