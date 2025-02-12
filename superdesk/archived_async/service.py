# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2025 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from copy import deepcopy
import logging
from typing import Any

from quart_babel import lazy_gettext as _

from apps.archive.common import BROADCAST_GENRE, ITEM_OPERATION, is_item_in_package
from apps.archived.archived import TAKES_PACKAGE
from apps.auth import get_user
from apps.legal_archive.commands import import_into_legal_archive
from apps.packages.package_service import PackageService
from apps.publish.content.common import ITEM_KILL
from apps.publish.content.kill import KillPublishService
from apps.publish.content.take_down import TakeDownPublishService
from superdesk.archive_async.service import ArchiveService, is_genre
from superdesk.core.app import get_current_app
from superdesk.core.resources.service import AsyncResourceService
from superdesk.core.types.search import ProjectedFieldArg, SearchRequest
from superdesk.errors import SuperdeskApiError
from superdesk.metadata.item import CONTENT_TYPE, PUBLISH_STATES
from superdesk.metadata.packages import MAIN_GROUP, RESIDREF
from superdesk.notification import push_notification
from superdesk.resource_fields import VERSION
from superdesk.types.archive import ArchiveResourceModel, ContentStates, GroupRefRefs, PubStatuses
from superdesk.types.archive import QUEUE_STATE
from superdesk.types.archived import ArchivedResourceModel
from superdesk.users.services import UsersService
from superdesk.utc import utcnow

logger = logging.getLogger(__name__)


class ArchivedService(AsyncResourceService[ArchivedResourceModel]):
    async def on_create(self, docs: list[ArchivedResourceModel]) -> None:
        package_service = PackageService()

        for doc in docs:
            # Remove fields that should not be in archived items
            doc.lock_user = None
            doc.lock_time = None
            doc.lock_action = None
            doc.lock_session = None
            doc.highlights = None
            doc.marked_desks = None
            doc.archived_id = self._get_archived_id(doc.item_id, doc.version)

            if doc.item_type == CONTENT_TYPE.COMPOSITE:
                # FIXME
                for ref in package_service.get_item_refs(doc):
                    ref["location"] = "archived"

    async def validate_delete_action(self, doc: ArchivedResourceModel, allow_all_types: bool = False) -> None:
        """Runs on delete of archive item.

        Overriding to validate the item being killed is actually eligible for kill. Validates the following:
            1. Is item of type Text?
            2. Is item a Broadcast Script?
            3. Does item acts as a Master Story for any of the existing broadcasts?
            4. Is item available in production or part of a normal package?
            5. Is the associated Digital Story is available in production or part of normal package?
            6. If item is a Take then is any take available in production or part of normal package?

        :param doc: represents the article in archived collection
        :param allow_all_types: represents if different types of documents are allowed to be killed
        :raises SuperdeskApiError.badRequestError() if any of the above validation conditions fail.
        """

        bad_req_error = SuperdeskApiError.badRequestError

        id_field = doc.id
        item_id = doc.item_id

        doc.item_id = str(id_field)
        doc.id = item_id

        if not allow_all_types and doc.item_type != CONTENT_TYPE.TEXT:
            raise bad_req_error(message=_("Only Text articles are allowed to be Killed in Archived repo"))

        if is_genre(doc, BROADCAST_GENRE):
            raise bad_req_error(message=_("Killing of Broadcast Items isn't allowed in Archived repo"))

        # FIXME: not an async service yet
        # broadcast_service = get_resource_service("archive_broadcast")
        # if await broadcast_service.get_broadcast_items_from_master_story(doc, True):
        #     raise bad_req_error(
        #         message=_("Can't kill as this article acts as a Master Story for existing broadcast(s)")
        #     )

        archive_service = ArchiveService()
        if await archive_service.find_one(None, guid_field=doc.guid):
            raise bad_req_error(message=_("Can't Kill as article is still available in production"))

        if not allow_all_types and is_item_in_package(doc):
            raise bad_req_error(message=_("Can't kill as article is part of a Package"))

        takes_package_id = self._get_take_package_id(doc)
        if takes_package_id:
            if await archive_service.find_by_id(takes_package_id):
                raise bad_req_error(message=_("Can't Kill as the Digital Story is still available in production"))

            takes_package = await self.find_one(item_id=takes_package_id, sort=[(VERSION, -1)])
            if not takes_package:
                raise bad_req_error(message=_("Digital Story of the article not found in Archived repo"))

            if not allow_all_types and is_item_in_package(takes_package):
                raise bad_req_error(message=_("Can't kill as Digital Story is part of a Package"))

            # FIXME
            for takes_ref in self._get_package_refs(takes_package):
                if takes_ref[RESIDREF] != doc.guid:
                    if await archive_service.find_by_id(takes_ref[RESIDREF]):
                        raise bad_req_error(message=_("Can't Kill as Take(s) are still available in production"))

                    take = await self.find_one(item_id=takes_ref[RESIDREF])
                    if not take:
                        raise bad_req_error(message=_("One of Take(s) not found in Archived repo"))

                    if not allow_all_types and is_item_in_package(take):
                        raise bad_req_error(message=_("Can't kill as one of Take(s) is part of a Package"))

        doc.item_id = item_id
        doc.id = id_field

    async def on_delete(self, doc: ArchivedResourceModel) -> None:
        await self.validate_delete_action(doc)

    # FIXME: incompatible override
    async def delete(self, lookup: dict[str, Any]) -> None:
        if get_current_app().testing and len(lookup) == 0:
            await super().delete(lookup)

    async def command_delete(self, lookup: dict[str, Any]) -> None:
        await super().delete(lookup)

    async def find_one(
        self,
        req: SearchRequest | None = None,
        projection: ProjectedFieldArg | None = None,
        use_mongo: bool = False,
        version: int | None = None,
        **lookup,
    ) -> ArchivedResourceModel | None:
        item = await super().find_one(req, **lookup)
        user = get_user()

        if (
            user
            and item
            # FIXME: UsersService is not async
            and str(item.task.stage) in UsersService.get_invisible_stages_ids(user.id)
        ):
            raise SuperdeskApiError.forbiddenError(_("User does not have permissions to read the item."))

        return item

    async def update(
        self,
        item_id: str | ObjectId,
        updates: dict[str, Any],
        etag: str | None = None,
        original: ArchivedResourceModel | None = None,
    ) -> None:
        """Runs on update of archive item.

        Overriding to handle with Kill/Takedown workflow in the Archived repo
        """

        if original is None:
            raise SuperdeskApiError.badRequestError()

        # Step 1
        articles_to_kill = await self.find_articles_to_kill({"_id": item_id})
        logger.info("Fetched articles to kill for id: %s", item_id)
        articles_to_kill.sort(key=lambda x: x.item_type, reverse=True)  # Needed because package has to be inserted last

        kill_service = KillPublishService() if updates.get(ITEM_OPERATION) == ITEM_KILL else TakeDownPublishService()
        updated = original.to_dict()

        for article in articles_to_kill:
            updates_copy = deepcopy(updates)
            await kill_service.apply_kill_override(article, updates_copy)
            updated.update(updates_copy)

            if original.flags and original.flags.marked_archived_only:
                await super().delete_many({"item_id": article.item_id})
                logger.info("Delete for article: %s", article.id)
                await kill_service.broadcast_kill_email(article, updates_copy)
                logger.info("Broadcast kill email for article: %s", article.id)
                continue

            await self._remove_and_set_kill_properties(article, articles_to_kill, updated)
            logger.info("Removing and setting properties for article: %s", article.id)

            # not async yet
            # transmission_details = await get_resource_service(LEGAL_PUBLISH_QUEUE_NAME).find(item_id=article.item_id)

            # if transmission_details:
            #     await get_enqueue_service(updates.get(ITEM_OPERATION, ITEM_KILL)).enqueue_archived_kill_item(
            #         article, transmission_details
            #     )

            article.id = article.item_id

            await super().delete_many({"item_id": article.id})
            logger.info("Delete for article: %s", article.id)

            docs = [article]
            archive_service = ArchiveService()
            await archive_service.create(docs)
            # FIXME: not async
            # await insert_into_versions(article)
            published_doc = deepcopy(article)
            published_doc.queue_state = QUEUE_STATE.QUEUED
            # FIXME not async yet
            # await get_resource_service("published").create([published_doc])
            logger.info("Insert into archive and published for article: %s", article.id)

            await import_into_legal_archive.apply_async(countdown=3, kwargs={"item_id": article.id})
            logger.info("Legal Archive import for article: %s", article.id)

            await kill_service.broadcast_kill_email(article, updates_copy)
            logger.info("Broadcast kill email for article: %s", article.id)

    async def on_updated(self, updates: dict[str, Any], original: ArchivedResourceModel) -> None:
        user = get_user()
        push_notification("item:deleted:archived", item=str(original.id), user=str(user.id))

    def on_fetched_item(self, doc: ArchivedResourceModel) -> None:
        # FIXME
        doc.type = "archived"

    def _get_archived_id(self, item_id: str, version: int) -> str:
        return f"{item_id}:{version}"

    async def get_archived_takes_package(
        self, package_id: str, take_id: str, version: int, include_other_takes: bool = True
    ) -> ArchivedResourceModel | None:
        # FIXME
        take_packages = await self.find(item_id=package_id, sort=[(VERSION, -1)])

        async for take_package in take_packages:
            # FIXME
            for ref in self._get_package_refs(take_package):
                if ref[RESIDREF] == take_id and (include_other_takes or ref["_current_version"] == version):
                    return take_package
        return None

    async def find_articles_to_kill(
        self, lookup: dict[str, Any], include_other_takes: bool = True
    ) -> list[ArchivedResourceModel]:
        """Finds the article to kill."""

        archived_doc = await self.find_one(**lookup)
        if not archived_doc:
            return []

        archived_doc = await self.find_one(item_id=archived_doc.item_id, sort=[(VERSION, -1)])
        if not archived_doc:
            return []

        articles_to_kill = [archived_doc]
        takes_package_id = self._get_take_package_id(archived_doc)

        if takes_package_id:
            takes_package = await self.get_archived_takes_package(
                takes_package_id, archived_doc.item_id, archived_doc.version, include_other_takes
            )
            if takes_package:
                articles_to_kill.append(takes_package)

                if include_other_takes:
                    # FIXME
                    for takes_ref in self._get_package_refs(takes_package):
                        if takes_ref[RESIDREF] != archived_doc.guid:
                            take = await self.find_one(item_id=takes_ref[RESIDREF], sort=[(VERSION, -1)])
                            if take:
                                articles_to_kill.append(take)

        return articles_to_kill

    async def _remove_and_set_kill_properties(
        self, article: ArchivedResourceModel, articles_to_kill: list[ArchivedResourceModel], updates: dict[str, Any]
    ) -> None:
        """Removes irrelevant properties and sets kill operation properties."""

        article.archived_id = None
        # FIXME
        article.type = None
        article.links = None
        # FIXME: None not allowed in queue state
        article.queue_state = None
        article.etag = None

        for field in ["headline", "abstract", "body_html"]:
            setattr(article, field, updates.get(field, getattr(article, field, "")))

        article.state = ContentStates.KILLED if updates[ITEM_OPERATION] == ITEM_KILL else ContentStates.RECALLED
        article.operation = updates["operation"]
        article.pubstatus = PubStatuses.CANCELED
        article.updated = utcnow()

        user = get_user()
        article.version_creator = str(user.id)

        # FIXME: what to use here?
        # resolve_document_version(article, ARCHIVE, "PATCH", article)

        if article.item_type == CONTENT_TYPE.COMPOSITE:
            package_service = PackageService()
            item_refs = package_service.get_item_refs(article)
            for ref in item_refs:
                item_in_package = [
                    item for item in articles_to_kill if item.item_id == ref[RESIDREF] or item.id == ref[RESIDREF]
                ]
                ref["location"] = ARCHIVE
                ref[VERSION] = item_in_package[0].version

    def _get_take_package_id(self, item: ArchivedResourceModel) -> str | None:
        """Gets the takes package ID if the item is in a takes package."""

        takes_package = [
            package.get("package")
            for package in item.linked_in_packages or []
            if package.get("package_type") == TAKES_PACKAGE
        ]
        if len(takes_package) > 1:
            message = f"Multiple takes found for item: {item.id}"
            logger.error(message)
        return takes_package[0] if takes_package else None

    def _get_package_refs(self, package: ArchivedResourceModel) -> GroupRefRefs | None:
        """Get refs from the takes package."""

        refs = None
        if package and package.groups:
            refs = next((group.refs for group in package.groups if group.id == MAIN_GROUP), None)
        return refs
