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
from typing import TYPE_CHECKING, Literal, cast
from apps.desks import DesksService
from eve.versioning import resolve_document_version

from superdesk.core import get_current_app, get_app_config
from superdesk.resource_fields import ID_FIELD, LAST_UPDATED
import superdesk
from collections import Counter
from eve.utils import ParsedRequest
from superdesk.errors import SuperdeskApiError
from superdesk import get_resource_service
from superdesk.metadata.item import ITEM_TYPE, CONTENT_TYPE, EMBARGO
from superdesk.metadata.packages import (
    LINKED_IN_PACKAGES,
    PACKAGE,
    REFS,
    RESIDREF,
    GROUPS,
    ID_REF,
    MAIN_GROUP,
    ROOT_GROUP,
    ROLE,
    ROOT_ROLE,
    MAIN_ROLE,
    GROUP_ID,
)
from apps.archive.common import ITEM_UNLINK, insert_into_versions_async
from superdesk.utc import utcnow
from superdesk.default_settings import VERSION
from quart_babel import gettext as _
from superdesk.signals import signals
from superdesk.validation import ValidationError
from superdesk.eve_async.service import AsyncBaseService
from apps.templates.content_templates import render_content_template_by_id

if TYPE_CHECKING:
    from apps.archive.archive import ArchiveService

logger = logging.getLogger(__name__)
package_create_signal = signals.signal("package.create")  # @UndefinedVariable
ARCHIVE = "archive"


def create_root_group(docs):
    """Define groups in given docs if not present or empty.

    :param docs: list of docs
    """
    for doc in docs:
        if len(doc.get(GROUPS, [])):
            continue
        doc[GROUPS] = [
            {GROUP_ID: ROOT_GROUP, ROLE: ROOT_ROLE, REFS: [{ID_REF: MAIN_GROUP}]},
            {GROUP_ID: MAIN_GROUP, ROLE: MAIN_ROLE, REFS: []},
        ]


def get_item_ref(item):
    """Get reference for given item which can be used in group.refs.

    :param item: item dict
    """
    return {
        RESIDREF: item.get("_id"),
        "headline": item.get("headline"),
        "slugline": item.get("slugline"),
        "location": "archive",
        "itemClass": "icls:" + item.get("type", "text"),
        "renditions": item.get("renditions", {}),
    }


async def copy_metadata_from_highlight_template(doc):
    """
    Copy the values set on highlight template

    :param doc
    """
    highlight_id = doc.get("highlight", None)
    if highlight_id:
        # We do late import to avoid circular import.
        from apps.highlights.service import HighlightsService

        highlights_service = get_resource_service("highlights")
        assert highlights_service is not None
        highlights_service = cast(HighlightsService, highlights_service)
        # TODO-ASYNC[highlights]: Use async method once HighlightsService is async.
        highlight = highlights_service.find_one(req=None, _id=highlight_id)
        if highlight and "template" in highlight:
            updates = await render_content_template_by_id(doc, highlight.get("template", None))
            if ITEM_TYPE in updates:
                del updates[ITEM_TYPE]
            doc.update(updates)


class PackageService:
    async def on_create_async(self, docs):
        create_root_group(docs)
        self.check_root_group(docs)
        await self.check_package_associations_async(docs)
        await self.check_not_in_personal_space_async(docs)

        for doc in docs:
            if not doc.get("ingest_provider"):
                doc["source"] = get_app_config("DEFAULT_SOURCE_VALUE_FOR_MANUAL_ARTICLES")

            if "highlight" in doc:
                await copy_metadata_from_highlight_template(doc)

        package_create_signal.send(self, docs=docs)

    async def on_created_async(self, docs):
        for doc, assoc in [(doc, assoc) for doc in docs for assoc in self._get_associations(doc)]:
            await self.update_link_async(doc, assoc)

    async def on_update_async(self, updates, original):
        self.check_root_group([updates])
        associations = self._get_associations(updates)
        await self.check_for_duplicates_async(original, associations)
        for assoc in associations:
            await self.extract_default_association_data_async(original, assoc)

    async def on_updated_async(self, updates, original):
        if updates.get(GROUPS):
            await self.update_groups_async(updates, original)

    async def update_groups_async(self, updates, original):
        to_add = {
            assoc.get(RESIDREF): assoc
            for assoc in self._get_associations(updates)
            if assoc.get(RESIDREF) and updates.get(GROUPS)
        }
        to_remove = (assoc for assoc in self._get_associations(original) if assoc.get(RESIDREF) not in to_add)
        for assoc in to_remove:
            await self.update_link_async(original, assoc, delete=True)
        for assoc_id in to_add.keys():
            await self.update_link_async(original, to_add[assoc_id])

    async def on_deleted_async(self, doc):
        for assoc in self._get_associations(doc):
            await self.update_link_async(doc, assoc, delete=True)

    def check_root_group(self, docs):
        for groups in [doc.get(GROUPS) for doc in docs if doc.get(GROUPS)]:
            self.check_all_groups_have_id_set(groups)
            root_groups = [group for group in groups if group.get(GROUP_ID) == ROOT_GROUP]

            if len(root_groups) == 0:
                message = _("Root group is missing.")
                logger.error(message)
                raise SuperdeskApiError.forbiddenError(message=message)

            if len(root_groups) > 1:
                message = _("Only one root group is allowed.")
                logger.error(message)
                raise SuperdeskApiError.forbiddenError(message=message)

            self.check_that_all_groups_are_referenced_in_root(root_groups[0], groups)

    def check_all_groups_have_id_set(self, groups):
        if any(group for group in groups if not group.get(GROUP_ID)):
            message = _("Group is missing id.")
            logger.error(message)
            raise SuperdeskApiError.forbiddenError(message=message)

    def check_that_all_groups_are_referenced_in_root(self, root, groups):
        rest = [group.get(GROUP_ID) for group in groups if group.get(GROUP_ID) != ROOT_GROUP]
        refs = [ref.get(ID_REF) for group in groups for ref in group.get(REFS, []) if ref.get(ID_REF)]

        rest_counter = Counter(rest)
        if any(id for id, value in rest_counter.items() if value > 1):
            message = _("{id} group is added multiple times.").format(id=id)
            logger.error(message)
            raise SuperdeskApiError.forbiddenError(message=message)

        if len(rest) != len(refs):
            message = _("The number of groups and of referenced groups in the root group do not match.")
            logger.error(message)
            raise SuperdeskApiError.forbiddenError(message=message)

        if len(set(rest).intersection(refs)) != len(refs):
            message = _("Not all groups are referenced in the root group.")
            logger.error(message)
            raise SuperdeskApiError.forbiddenError(message=message)

    async def check_package_associations_async(self, docs):
        for doc, group in ((doc, group) for doc in docs for group in doc.get(GROUPS, [])):
            associations = group.get(REFS, [])
            await self.check_for_duplicates_async(doc, associations)
            for assoc in associations:
                await self.extract_default_association_data_async(group, assoc)

    async def check_not_in_personal_space_async(self, docs):
        """Verify that the package is not in the user personal space.

        Retrieving details for the list of packages an item was linked in does not
        contain packages that were in other users' personal space. One can't spike
        items if it can't remove it from the packages it belongs to.
        """
        for doc in docs:
            # the next 'particular_type' containing line is liveblog related and it is usefull since
            # liveblog users don't have a personal space. Therefore, if the the task/desk condition
            # is in place, it prevents the liveblog posts from beeing published.
            if not doc.get("particular_type"):
                if not doc.get("task") or not doc["task"].get("desk"):
                    message = "Packages can not be created in the personal space."
                    logger.error(message)
                    raise SuperdeskApiError.forbiddenError(message=message)
                if not doc["task"].get("stage"):
                    desks_service = get_resource_service("desks")
                    assert desks_service is not None
                    desks_service = cast(DesksService, desks_service)
                    desk = await desks_service.find_one_async(req=None, _id=doc["task"]["desk"])
                    doc["task"]["stage"] = desk["working_stage"]

    async def extract_default_association_data_async(self, package, assoc):
        if assoc.get(ID_REF):
            return

        item, item_id, endpoint = await self.get_associated_item_async(assoc)
        await self.check_for_circular_reference_async(package, item_id)
        assoc["guid"] = item.get("guid", item_id)
        assoc["type"] = item.get("type")

    async def get_associated_item_async(self, assoc, throw_if_not_found=True):
        endpoint = assoc.get("location", "archive")
        item_id = assoc.get(RESIDREF)

        if not item_id:
            raise SuperdeskApiError.badRequestError(_("Package contains empty ResidRef!"))

        service = get_resource_service(endpoint)
        assert service is not None
        service = cast(AsyncBaseService, service)
        item = await service.find_one_async(req=None, _id=item_id)

        if not item and throw_if_not_found:
            message = _("Invalid item reference: {reference}").format(reference=assoc.get(RESIDREF))
            logger.error(message)
            raise SuperdeskApiError.notFoundError(message=message)
        return item, item_id, endpoint

    async def update_link_async(self, package, assoc, delete=False):
        # skip root node
        if assoc.get(ID_REF):
            return
        package_id = package[ID_FIELD]

        item, item_id, endpoint = await self.get_associated_item_async(assoc, not delete)
        if not item and delete:
            # just exit, no point on complaining
            return

        two_way_links = [d for d in item.get(LINKED_IN_PACKAGES, []) if not d["package"] == package_id]

        if not delete:
            data = {PACKAGE: package_id}
            two_way_links.append(data)

        updates = {LINKED_IN_PACKAGES: two_way_links}
        service = get_resource_service(endpoint)
        assert service is not None
        service = cast(AsyncBaseService, service)
        await service.system_update_async(item_id, updates, item)

    async def check_for_duplicates_async(self, package, associations):
        counter = Counter()
        package_id = package[ID_FIELD]
        for itemRef in [assoc[RESIDREF] for assoc in associations if assoc.get(RESIDREF)]:
            if itemRef == package_id:
                message = _("Trying to self reference as an association.")
                logger.error(message)
                raise SuperdeskApiError.forbiddenError(message=message)
            counter[itemRef] += 1

        if any(itemRef for itemRef, value in counter.items() if value > 1):
            message = _("Content associated multiple times")
            logger.error(message)
            raise SuperdeskApiError.forbiddenError(message=message)

    async def check_for_circular_reference_async(self, package, item_id):
        if any(d for d in package.get(LINKED_IN_PACKAGES, []) if d["package"] == item_id):
            message = _("Trying to create a circular reference to: {item_id}").format(item_id=item_id)
            logger.error(message)
            raise ValidationError(message)
        else:
            # keep checking in the hierarchy
            archive_service = get_resource_service(ARCHIVE)
            assert archive_service is not None
            if TYPE_CHECKING:
                archive_service = cast(ArchiveService, archive_service)
            for d in (d for d in package.get(LINKED_IN_PACKAGES, []) if "package" in d):
                linked_package = await archive_service.find_one_async(req=None, _id=d["package"])
                if linked_package:
                    await self.check_for_circular_reference_async(linked_package, item_id)

    async def get_packages_async(self, doc_id, not_package_id=None):
        """
        Retrieves package(s) if an article identified by doc_id is referenced in a package.

        :param str doc_id: identifier of the item in the package
        :param str not_package_id: not package id
        :return: articles of type composite
        """

        query = {"$and": [{ITEM_TYPE: CONTENT_TYPE.COMPOSITE}, {"groups.refs.residRef": doc_id}]}

        if not_package_id:
            query["$and"].append({ID_FIELD: {"$ne": not_package_id}})

        request = ParsedRequest()
        request.max_results = 100

        archive_service = get_resource_service(ARCHIVE)
        assert archive_service is not None
        if TYPE_CHECKING:
            archive_service = cast(ArchiveService, archive_service)
        return await archive_service.get_from_mongo_async(req=request, lookup=query)

    def remove_ref_from_inmem_package(self, package, ref_id):
        """Removes the reference with ref_id from non-root groups.

        If there is nothing left
        in that group then the group and its reference in root group is also removed.
        If the removed item was the last item then returns

        :param package: Package
        :param ref_id: Id of the reference to be removed
        :return: True if there are still references in the package, False otherwise
        """
        groups_to_be_removed = set()
        non_root_groups = [group for group in package.get(GROUPS, []) if group.get(GROUP_ID) != ROOT_GROUP]
        for non_rg in non_root_groups:
            refs = [r for r in non_rg.get(REFS, []) if r.get(RESIDREF, "") != ref_id]
            if len(refs) == 0:
                groups_to_be_removed.add(non_rg.get(GROUP_ID))
            non_rg[REFS] = refs

        if len(groups_to_be_removed) > 0:
            root_group = [group for group in package.get(GROUPS, []) if group.get(GROUP_ID) == ROOT_GROUP][0]
            refs = [r for r in root_group.get(REFS, []) if r.get(ID_REF) not in groups_to_be_removed]
            root_group[REFS] = refs
            removed_groups = [
                group for group in package.get(GROUPS, []) if group.get(GROUP_ID) not in groups_to_be_removed
            ]
            package[GROUPS] = removed_groups

            # return if the package has any items left in it
            return len(refs) > 0

        # still has items in the package
        return True

    async def replace_ref_in_package_async(self, package, old_ref_id, new_ref_id):
        """Locates the reference with the old_ref_id and replaces with the new_ref_id

        :param package: Package
        :param old_ref_id: Old reference id
        :param new_ref_id: New reference id
        """
        archive_service = get_resource_service("archive")
        assert archive_service is not None
        if TYPE_CHECKING:
            archive_service = cast(ArchiveService, archive_service)
        new_item = await archive_service.find_one_async(req=None, _id=new_ref_id)

        non_root_groups = (group for group in package.get(GROUPS, []) if group.get(GROUP_ID) != ROOT_GROUP)
        for g in (ref for group in non_root_groups for ref in group.get(REFS, [])):
            if g.get(RESIDREF, "") == old_ref_id:
                g[RESIDREF] = new_ref_id
                g["guid"] = new_ref_id
                g[VERSION] = new_item[VERSION]

    def update_field_in_package(self, package, ref_id, field, field_value):
        """Locates the reference with the ref_id and replaces field value

        :param package: Package
        :param ref_id: reference id
        :param field: field to be replaced
        :param field_value: value to be used
        """
        non_root_groups = (group for group in package.get(GROUPS, []) if group.get(GROUP_ID) != ROOT_GROUP)
        for g in (ref for group in non_root_groups for ref in group.get(REFS, [])):
            if g.get(RESIDREF, "") == ref_id:
                g[field] = field_value

    def remove_group_ref(self, package, ref_id):
        groups = package[GROUPS]
        new_groups = [
            {
                GROUP_ID: group[GROUP_ID],
                ROLE: group.get(ROLE),
                REFS: [ref for ref in group[REFS] if ref.get("guid") != ref_id],
            }
            for group in groups
        ]
        new_root_refs = [{ID_REF: group[GROUP_ID]} for group in new_groups if group[GROUP_ID] != ROOT_GROUP]

        for group in new_groups:
            if group[GROUP_ID] == ROOT_GROUP:
                group[REFS] = new_root_refs
                break

        return new_groups

    async def remove_refs_in_package_async(self, package, ref_id_to_remove, processed_packages=None):
        """Removes residRef referenced by ref_id_to_remove from the package associations and returns the package id.

        Before removing checks if the package has been processed. If processed the package is skipped.

        :return: package[config.ID_FIELD]
        """
        groups = package[GROUPS]

        if processed_packages is None:
            processed_packages = []

        sub_package_ids = [
            ref["guid"] for group in groups for ref in group[REFS] if ref.get("type") == CONTENT_TYPE.COMPOSITE
        ]
        for sub_package_id in sub_package_ids:
            if sub_package_id not in processed_packages:
                sub_package = await self.find_one_async(req=None, _id=sub_package_id)
                await self.remove_refs_in_package_async(sub_package, ref_id_to_remove, processed_packages)

        new_groups = self.remove_group_ref(package, ref_id_to_remove)
        updates = {LAST_UPDATED: utcnow(), GROUPS: new_groups}

        resolve_document_version(updates, ARCHIVE, "PATCH", package)
        archive_service = get_resource_service("archive")
        assert archive_service is not None
        if TYPE_CHECKING:
            archive_service = cast(ArchiveService, archive_service)
        await archive_service.patch_async(package[ID_FIELD], updates)

        app = get_current_app().as_any()
        app.on_archive_item_updated(updates, package, ITEM_UNLINK)
        await insert_into_versions_async(id_=package[ID_FIELD])

        sub_package_ids.append(package[ID_FIELD])
        return sub_package_ids

    def _get_associations(self, doc):
        return [assoc for group in doc.get(GROUPS, []) for assoc in group.get(REFS, [])]

    async def remove_spiked_refs_from_package_async(self, doc_id, not_package_id=None):
        packages_cursor = await self.get_packages_async(doc_id, not_package_id)
        packages = await packages_cursor.to_list(None)
        if not packages:
            return

        processed_packages = []
        for package in packages:
            if str(package[ID_FIELD]) in processed_packages:
                continue

            processed_packages.extend(await self.remove_refs_in_package_async(package, doc_id, processed_packages))

    def get_residrefs(self, package):
        """
        Returns all residref in the package.

        :param package:
        :return: list of residref
        """
        return [
            ref.get(RESIDREF) for group in package.get(GROUPS, []) for ref in group.get(REFS, []) if RESIDREF in ref
        ]

    async def check_if_any_item_in_package_has_embargo(self, package):
        """Recursively checks if any item in the package has embargo.

        :raises: SuperdeskApiError.badRequestError() if any item in the package has embargo.
        """

        item_refs_in_package = self.get_residrefs(package)

        archive_service = get_resource_service("archive")
        assert archive_service is not None
        if TYPE_CHECKING:
            archive_service = cast(ArchiveService, archive_service)

        for item_ref in item_refs_in_package:
            doc = await archive_service.find_one_async(req=None, _id=item_ref)

            if doc and doc.get(EMBARGO):
                raise SuperdeskApiError.badRequestError(
                    _("Package can't have item which has embargo. ")
                    + _("Slugline/Unique Name of the item having embargo: {slugline}/{unique}").format(
                        slugline=doc.get("slugline"), unique=doc.get("unique_name")
                    )
                )

            if doc and doc[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE:
                await self.check_if_any_item_in_package_has_embargo(doc)

    def get_item_refs(self, package):
        """Returns all item references in the package.

        :param package:
        :return: list of item references
        """

        return [ref for group in package.get(GROUPS, []) for ref in group.get(REFS, []) if RESIDREF in ref]

    def get_linked_in_package_ids(self, item):
        """Returns all linked in package ids for an item

        :param dict item:
        :return list: list of package ids
        """
        return [package_link.get(PACKAGE) for package_link in item.get(LINKED_IN_PACKAGES, []) or []]

    def get_linked_in_packages(self, item):
        """Returns all linked in packages for an item

        :param dict item:
        :return list: list of package ids
        """

        return [package for package in item.get(LINKED_IN_PACKAGES, [])]

    def is_package(self, item):
        """Test if given item is a package

        :param dict item: item to check
        """
        return item[ITEM_TYPE] == CONTENT_TYPE.COMPOSITE
