from typing import Any
from quart_babel import gettext as _

from superdesk import get_resource_service
from superdesk.activity import add_activity, ACTIVITY_UPDATE
from superdesk.core import get_app_config
from superdesk.core.resources import AsyncResourceService
from superdesk.errors import SuperdeskApiError
from superdesk.notification import push_notification
from superdesk.resource_fields import ID_FIELD
from superdesk.types import DesksResourceModel
from superdesk.types.enums import DeskTypeEnum


class DesksAsyncService(AsyncResourceService[DesksResourceModel]):
    notification_key = "desk"

    async def create(self, docs: list[DesksResourceModel]) -> list[str]:
        """Creates new desk.

        Overriding to check if the desk being created has Working and Incoming Stages. If not then Working and Incoming
        Stages would be created and associates them with the desk and desk with the Working and Incoming Stages.
        Also sets desk_type.

        :return: list of desk id's
        """

        for desk in docs:
            stages_to_be_linked_with_desk = []
            stage_service = get_resource_service("stages")
            self._ensure_unique_members(desk.to_dict())

            if desk.content_expiry == 0:
                desk.content_expiry = get_app_config("CONTENT_EXPIRY_MINUTES")

            if desk.working_stage is None:
                stages_to_be_linked_with_desk.append("working_stage")
                stage_id = stage_service.create_working_stage()
                desk.working_stage = stage_id[0]

            if desk.incoming_stage is None:
                stages_to_be_linked_with_desk.append("incoming_stage")
                stage_id = stage_service.create_incoming_stage()
                desk.incoming_stage = stage_id[0]

            desk.desk_type = DeskTypeEnum.AUTHORING
            await super().create([desk])
            for stage_type in stages_to_be_linked_with_desk:
                stage_service.patch(desk.to_dict()[stage_type], {"desk": desk.id})

            # make the desk available in default content template
            content_templates = get_resource_service("content_templates")
            template = content_templates.find_one(req=None, _id=desk.default_content_template)
            if template:
                template.setdefault("template_desks", []).append(desk.id)
                content_templates.patch(desk.default_content_template, template)

        return [str(doc.id) for doc in docs]

    async def on_created(self, docs: list[DesksResourceModel]) -> None:
        for doc in docs:
            push_notification(self.notification_key, created=1, desk_id=str(doc.id))
            get_resource_service("users").update_stage_visibility_for_users()

    async def on_update(self, updates: dict[str, Any], original: DesksResourceModel) -> None:
        if updates.get("content_expiry") == 0:
            updates["content_expiry"] = None

        self._ensure_unique_members(updates)

        if updates.get("desk_type") and updates.get("desk_type") != original.desk_type:
            archive_versions_query = {
                "$or": [
                    {"task.last_authoring_desk": str(original.id)},
                    {"task.last_production_desk": str(original.id)},
                ]
            }

            items = get_resource_service("archive_versions").get(req=None, lookup=archive_versions_query)
            if items and items.count():
                raise SuperdeskApiError.badRequestError(
                    message=_("Cannot update Desk Type as there are article(s) referenced by the Desk.")
                )

    async def on_updated(self, updates: dict[str, Any], original: DesksResourceModel) -> None:
        await self.__send_notification(updates, original)

    async def on_delete(self, doc: DesksResourceModel):
        """Runs on desk delete.

        Overriding to prevent deletion of a desk if the desk meets one of the below conditions:
            1. The desk isn't assigned as a default desk to user(s)
            2. The desk has no content
            3. The desk is associated with routing rule(s)
        """

        as_default_desk = get_resource_service("users").get(req=None, lookup={"desk": doc.id})
        if as_default_desk and as_default_desk.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as it is assigned as default desk to user(s).")
            )

        routing_rules_query = {
            "$or": [
                {"rules.actions.fetch.desk": doc.id},
                {"rules.actions.publish.desk": doc.id},
            ]
        }
        routing_rules = get_resource_service("routing_schemes").get(req=None, lookup=routing_rules_query)
        if routing_rules and routing_rules.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as routing scheme(s) are associated with the desk")
            )

        archive_versions_query = {
            "$or": [
                {"task.desk": str(doc.id)},
                {"task.last_authoring_desk": str(doc.id)},
                {"task.last_production_desk": str(doc.id)},
            ]
        }

        items = get_resource_service("archive_versions").get(req=None, lookup=archive_versions_query)
        if items and items.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as it has article(s) or referenced by versions of the article(s).")
            )

    async def delete_many(self, lookup: dict[str, Any]) -> list[str]:
        """
        Overriding to delete stages before deleting a desk
        """

        get_resource_service("stages").delete(lookup={"desk": lookup.get(ID_FIELD)})
        return await super().delete_many(lookup)

    async def on_deleted(self, doc: DesksResourceModel):
        desk_user_ids = [str(member["user"]) for member in doc.members]
        push_notification(self.notification_key, deleted=1, user_ids=desk_user_ids, desk_id=str(doc.id))

    async def __send_notification(self, updates: dict[str, Any], desk: DesksResourceModel):
        desk_id = desk.id
        users_service = get_resource_service("users")

        if "members" in updates:
            added, removed = self.__compare_members(desk.members, updates["members"])
            if len(removed) > 0:
                push_notification(
                    "desk_membership_revoked", updated=1, user_ids=[str(item) for item in removed], desk_id=str(desk_id)
                )

            for added_user in added:
                user = users_service.find_one(req=None, _id=added_user)
                activity = add_activity(
                    ACTIVITY_UPDATE,
                    "user {{user}} has been added to desk {{desk}}: Please re-login.",
                    self.resource_name,
                    notify=added,
                    can_push_notification=False,
                    user=user.get("username"),
                    desk=desk.name,
                )
                push_notification("activity", _dest=activity["recipients"])
                users_service.update_stage_visibility_for_user(user)

            for removed_user in removed:
                user = users_service.find_one(req=None, _id=removed_user)
                users_service.update_stage_visibility_for_user(user)

        else:
            push_notification(self.notification_key, updated=1, desk_id=str(desk_id))

    def __compare_members(self, original, updates):
        original_members = set([member["user"] for member in original])
        updates_members = set([member["user"] for member in updates])
        added = updates_members - original_members
        removed = original_members - updates_members
        return added, removed

    def _ensure_unique_members(self, doc: dict[str, Any]):
        """Ensure the members are unique"""
        if doc.get("members"):
            # ensuring that members list is unique
            doc["members"] = [{"user": user} for user in {member.get("user") for member in doc.get("members", [])}]
