# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
import json
import logging
import itertools
from typing import Dict, Any, List

import superdesk

from superdesk.core import get_app_config, get_current_app
from superdesk.resource_fields import ID_FIELD
from superdesk.types import UsersResourceModel
from superdesk.flask import request
from superdesk import get_resource_service
from superdesk.errors import SuperdeskApiError
from superdesk.resource import Resource
from superdesk.utils import SuperdeskBaseEnum
from superdesk.timer import timer
from bson.objectid import ObjectId
from superdesk.eve_async.service import AsyncBaseService
from superdesk.notification import push_notification
from superdesk.activity import add_activity, ACTIVITY_UPDATE
from superdesk.metadata.item import FAMILY_ID, ITEM_STATE, CONTENT_STATE
from eve.utils import ParsedRequest
from quart_babel import gettext as _, lazy_gettext


logger = logging.getLogger(__name__)

SIZE_MAX = 1000  # something reasonable for the ui


class DeskTypes(SuperdeskBaseEnum):
    authoring = "authoring"
    production = "production"


desks_schema = {
    "name": {"type": "string", "required": True, "nullable": False, "empty": False, "iunique": True},
    "description": {"type": "string"},
    "members": {"type": "list", "schema": {"type": "dict", "schema": {"user": Resource.rel("users", True)}}},
    "incoming_stage": Resource.rel("stages", True),
    "working_stage": Resource.rel("stages", True),
    "content_expiry": {"type": "integer"},
    "source": {"type": "string"},
    "send_to_desk_not_allowed": {"type": "boolean"},
    "monitoring_settings": {
        "type": "list",
        "schema": {
            "type": "dict",
            "schema": {
                "_id": {"type": "string", "required": True},
                "type": {
                    "type": "string",
                    "allowed": ["search", "stage", "scheduledDeskOutput", "deskOutput", "personal", "sentDeskOutput"],
                    "required": True,
                },
                "max_items": {"type": "integer", "required": True},
            },
        },
    },
    "desk_type": {"type": "string", "default": DeskTypes.authoring.value, "allowed": DeskTypes.values()},
    "desk_metadata": {
        "type": "dict",
    },
    "content_profiles": {
        "type": "dict",
    },
    "desk_language": {"type": "string"},
    "monitoring_default_view": {"type": "string", "allowed": ["", "list", "swimlane", "photogrid"], "required": False},
    "default_content_profile": Resource.rel("content_types", type="string", nullable=True),
    "default_content_template": Resource.rel("content_templates", nullable=True),
    # name of a Slack channel that may be associated with the desk
    "slack_channel_name": {"type": "string"},
    # desk prefered vocabulary items
    "preferred_cv_items": {
        "type": "dict",
    },
    # if the preserve_published_content is set to true then the content on this won't be expired
    "preserve_published_content": {"type": "boolean", "required": False, "default": False},
    # Store SAMS's Desk settings on the Desk items
    "sams_settings": {"type": "dict", "allow_unknown": True, "schema": {"allowed_sets": {"type": "list"}}},
    "email": {"type": "string", "nullable": True},
}


def init_app(app) -> None:
    endpoint_name = "desks"
    service: Any = DesksService(endpoint_name, backend=superdesk.get_backend())
    DesksResource(endpoint_name, app=app, service=service)
    endpoint_name = "user_desks"
    service = UserDesksService(endpoint_name, backend=superdesk.get_backend())
    UserDesksResource(endpoint_name, app=app, service=service)
    endpoint_name = "sluglines"
    service = SluglineDeskService(endpoint_name, backend=superdesk.get_backend())
    SluglineDesksResource(endpoint_name, app=app, service=service)
    endpoint_name = "desk_overview"
    service = OverviewService(endpoint_name, backend=superdesk.get_backend())
    OverviewResource(endpoint_name, app=app, service=service)
    endpoint_name = "desk_users"
    service = DeskUsersService(endpoint_name, backend=superdesk.get_backend())
    DeskUsersResource(endpoint_name, app=app, service=service)


superdesk.privilege(
    name="desks", label=lazy_gettext("Desk Management"), description=lazy_gettext("User can manage desks.")
)
superdesk.privilege(
    name="masterdesk", label=lazy_gettext("Master Desk"), description=lazy_gettext("User can access master desk.")
)


class DesksResource(Resource):
    schema = desks_schema
    privileges = {"POST": "desks", "PATCH": "desks", "DELETE": "desks"}
    datasource = {"default_sort": [("name", 1)]}
    mongo_indexes = {
        "name_1": ([("name", 1)], {"unique": True}),
    }


class DesksService(AsyncBaseService):
    notification_key = "desk"

    async def create_async(self, docs, **kwargs):
        """Creates new desk.

        Overriding to check if the desk being created has Working and Incoming Stages. If not then Working and Incoming
        Stages would be created and associates them with the desk and desk with the Working and Incoming Stages.
        Also sets desk_type.

        :return: list of desk id's
        """

        for desk in docs:
            stages_to_be_linked_with_desk = []
            stage_service = superdesk.get_resource_service("stages")
            self._ensure_unique_members(desk)

            if desk.get("content_expiry") == 0:
                desk["content_expiry"] = get_app_config("CONTENT_EXPIRY_MINUTES")

            if "working_stage" not in desk:
                stages_to_be_linked_with_desk.append("working_stage")
                stage_id = stage_service.create_working_stage()
                desk["working_stage"] = stage_id[0]

            if "incoming_stage" not in desk:
                stages_to_be_linked_with_desk.append("incoming_stage")
                stage_id = stage_service.create_incoming_stage()
                desk["incoming_stage"] = stage_id[0]

            desk.setdefault("desk_type", DeskTypes.authoring.value)
            await super().create_async([desk], **kwargs)
            for stage_type in stages_to_be_linked_with_desk:
                stage_service.patch(desk[stage_type], {"desk": desk[ID_FIELD]})

            # make the desk available in default content template
            content_templates = get_resource_service("content_templates")
            template = await content_templates.find_one_async(req=None, _id=desk.get("default_content_template"))
            if template:
                template.setdefault("template_desks", []).append(desk.get(ID_FIELD))
                await content_templates.patch_async(desk.get("default_content_template"), template)

        return [doc[ID_FIELD] for doc in docs]

    async def on_created_async(self, docs):
        user_service = UsersResourceModel.get_service()
        for doc in docs:
            push_notification(self.notification_key, created=1, desk_id=str(doc.get(ID_FIELD)))
            await user_service.update_stage_visibility_for_users()

    async def on_update_async(self, updates, original):
        if updates.get("content_expiry") == 0:
            updates["content_expiry"] = None

        self._ensure_unique_members(updates)

        if updates.get("desk_type") and updates.get("desk_type") != original.get("desk_type", ""):
            archive_versions_query = {
                "$or": [
                    {"task.last_authoring_desk": str(original[ID_FIELD])},
                    {"task.last_production_desk": str(original[ID_FIELD])},
                ]
            }

            items = superdesk.get_resource_service("archive_versions").get(req=None, lookup=archive_versions_query)
            if items and items.count():
                raise SuperdeskApiError.badRequestError(
                    message=_("Cannot update Desk Type as there are article(s) referenced by the Desk.")
                )

    def _ensure_unique_members(self, doc):
        """Ensure the members are unique"""
        if doc.get("members"):
            # ensuring that members list is unique
            doc["members"] = [{"user": user} for user in {member.get("user") for member in doc.get("members")}]

    async def on_updated_async(self, updates, original):
        await self.__send_notification(updates, original)

    async def on_delete_async(self, desk):
        """Runs on desk delete.

        Overriding to prevent deletion of a desk if the desk meets one of the below conditions:
            1. The desk isn't assigned as a default desk to user(s)
            2. The desk has no content
            3. The desk is associated with routing rule(s)
        """

        if await UsersResourceModel.get_service().count({"desk": desk[ID_FIELD]}):
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as it is assigned as default desk to user(s).")
            )

        routing_rules_query = {
            "$or": [
                {"rules.actions.fetch.desk": desk[ID_FIELD]},
                {"rules.actions.publish.desk": desk[ID_FIELD]},
            ]
        }
        routing_rules = superdesk.get_resource_service("routing_schemes").get(req=None, lookup=routing_rules_query)
        if routing_rules and routing_rules.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as routing scheme(s) are associated with the desk")
            )

        archive_versions_query = {
            "$or": [
                {"task.desk": str(desk[ID_FIELD])},
                {"task.last_authoring_desk": str(desk[ID_FIELD])},
                {"task.last_production_desk": str(desk[ID_FIELD])},
            ]
        }

        items = superdesk.get_resource_service("archive_versions").get(req=None, lookup=archive_versions_query)
        if items and items.count():
            raise SuperdeskApiError.preconditionFailedError(
                message=_("Cannot delete desk as it has article(s) or referenced by versions of the article(s).")
            )

    async def delete_async(self, lookup):
        """
        Overriding to delete stages before deleting a desk
        """

        superdesk.get_resource_service("stages").delete(lookup={"desk": lookup.get(ID_FIELD)})
        await super().delete_async(lookup)

    async def on_deleted_async(self, doc):
        desk_user_ids = [str(member["user"]) for member in doc.get("members", [])]
        push_notification(self.notification_key, deleted=1, user_ids=desk_user_ids, desk_id=str(doc.get(ID_FIELD)))

    def __compare_members(self, original, updates):
        original_members = set([member["user"] for member in original])
        updates_members = set([member["user"] for member in updates])
        added = updates_members - original_members
        removed = original_members - updates_members
        return added, removed

    async def __send_notification(self, updates, desk):
        desk_id = desk[ID_FIELD]
        users_service = UsersResourceModel.get_service()

        if "members" in updates:
            added, removed = self.__compare_members(desk.get("members", {}), updates["members"])
            if len(removed) > 0:
                push_notification(
                    "desk_membership_revoked", updated=1, user_ids=[str(item) for item in removed], desk_id=str(desk_id)
                )

            for added_user in added:
                user = await users_service.find_by_id(added_user)
                activity = await add_activity(
                    ACTIVITY_UPDATE,
                    "user {{user}} has been added to desk {{desk}}: Please re-login.",
                    self.datasource,
                    notify=added,
                    can_push_notification=False,
                    user=user.username,
                    desk=desk.get("name"),
                )
                push_notification("activity", _dest=activity["recipients"])
                await users_service.update_stage_visibility_for_user(user)

            for removed_user in removed:
                user = await users_service.find_by_id(removed_user)
                await users_service.update_stage_visibility_for_user(user)

        else:
            push_notification(self.notification_key, updated=1, desk_id=str(desk.get(ID_FIELD)))

    # TODO-ASYNC: Remove this once is't no longer used anywhere
    def get_desk_name(self, desk_id):
        """Return the item desk.

        :param desk_id:
        :return dict: desk document
        """
        desk_name = ""
        desk = self.find_one(req=None, _id=desk_id)
        if desk:
            desk_name = desk.get("name") or ""

        return desk_name

    async def get_desk_name_async(self, desk_id):
        """Return the item desk.

        :param desk_id:
        :return dict: desk document
        """
        desk_name = ""
        desk = await self.find_one_async(req=None, _id=desk_id)
        if desk:
            desk_name = desk.get("name") or ""

        return desk_name

    async def on_fetched_async(self, res):
        members_set = set()
        db_users = get_current_app().data.mongo_async.pymongo("users").db["users"]

        # find display_name from the users document for each member in desks document
        for desk in res["_items"]:
            if "members" in desk:
                users = await db_users.find(
                    {"_id": {"$in": [member["user"] for member in desk.get("members", [])]}}, {"display_name": 1}
                ).to_list()
                members_set |= {(m["_id"], m["display_name"]) for m in users}

        if members_set:
            members_list = list(members_set)
            members_list.sort(key=lambda k: k[1].lower())
            sorted_members_ids = tuple(m[0] for m in members_list)

            # sort the members of each desk according to ordered_dict
            for desk in res["_items"]:
                if "members" in desk:
                    # remove members which don't exist in db
                    desk["members"] = [member for member in desk["members"] if member["user"] in sorted_members_ids]
                    # sort member in desk
                    desk["members"].sort(key=lambda x: sorted_members_ids.index(x["user"]))

        return res


class UserDesksResource(Resource):
    url = 'users/<regex("[a-f0-9]{24}"):user_id>/desks'
    resource_title = "user_desks"
    schema = desks_schema
    datasource = {"source": "desks", "default_sort": [("name", 1)]}
    resource_methods = ["GET"]


class UserDesksService(AsyncBaseService):
    async def get_async(self, req, lookup):
        if lookup.get("user_id"):
            lookup["members.user"] = ObjectId(lookup["user_id"])
            del lookup["user_id"]
        return await super().get_async(req, lookup)

    # TODO-ASYNC: Convert this to async when upgrading archive module
    def is_member(self, user_id, desk_id):
        # desk = list(self.get(req=None, lookup={'members.user':ObjectId(user_id), '_id': ObjectId(desk_id)}))
        return len(list(self.get(req=None, lookup={"members.user": ObjectId(user_id), "_id": ObjectId(desk_id)}))) > 0

    # TODO-ASYNC: Convert this to async when upgrading archive module
    def get_by_user(self, user_id):
        return list(self.get(req=None, lookup={"user_id": user_id}))


class DeskUsersResource(Resource):
    url = 'desks/<regex("[a-f0-9]{24}"):desk_id>/users'
    resource_title = "desk_users"
    datasource = {
        "source": "users",
        "default_sort": [("username", 1)],
        "projection": {
            "username": 1,
            "first_name": 1,
            "last_name": 1,
            "display_name": 1,
            "email": 1,
            "picture_url": 1,
            "avatar": 1,
            "avatar_renditions": 1,
            "role": 1,
            "last_activity_at": 1,
            "sign_off": 1,
        },
    }
    resource_methods = ["GET"]


class DeskUsersService(AsyncBaseService):
    async def get_async(self, req, lookup):
        desk_id = lookup.pop("desk_id", None)
        desks_service = superdesk.get_resource_service("desks")
        if desk_id:
            desk = await desks_service.find_one_async(req=None, _id=ObjectId(desk_id))
            if desk and desk.get("members"):
                lookup["_id"] = {"$in": [member["user"] for member in desk.get("members", [])]}
            else:
                lookup["_id"] = ""  # return empty result
        return await super().get_async(req, lookup)


class SluglineDesksResource(Resource):
    url = 'desks/<regex("[a-f0-9]{24}"):desk_id>/sluglines'
    datasource = {
        "source": "published",
        "search_backend": "elastic",
        "default_sort": [("slugline.phrase", 1), ("versioncreated", 0)],
        "elastic_filter": {
            "and": [
                {"range": {"versioncreated": {"gte": "now-24H"}}},
                {"term": {"last_published_version": True}},
                {"term": {"type": "text"}},
            ]
        },
    }
    resource_methods = ["GET"]
    item_methods = []
    schema = {
        "place": {"type": "string"},
        "items": {"type": "list"},
    }


class SluglineDeskService(AsyncBaseService):
    SLUGLINE = "slugline"
    OLD_SLUGLINES = "old_sluglines"
    VERSION_CREATED = "versioncreated"
    HEADLINE = "headline"
    NAME = "name"
    PLACE = "place"
    GROUP = "group"

    def _get_slugline_with_legal(self, article):
        """If the article is set to be legal adds 'Legal:' prefix for slugline.

        :param article:
        :return:
        """
        is_legal = article.get("flags", {}).get("marked_for_legal", False)
        if is_legal:
            return "{}: {}".format("Legal", article.get(self.SLUGLINE, ""))
        else:
            return article.get(self.SLUGLINE, "")

    async def get_async(self, req, lookup):
        """Return desk item summary.

        Given the desk the function will return a summary of the sluglines and headlines published from that
        desk in the last 24 hours. Domestic items are grouped together, rest of the world items are group
        by their place names.

        :param req:
        :param lookup:
        :return:
        """
        lookup["task.desk"] = lookup["desk_id"]
        lookup.pop("desk_id")
        req.max_results = 1000
        desk_items = await super().get_async(req, lookup)

        # domestic docs
        docs = []
        # rest of the world docs
        row_docs = []
        async for item in desk_items:
            slugline = self._get_slugline_with_legal(item)
            headline = item.get(self.HEADLINE)
            versioncreated = item.get(self.VERSION_CREATED)
            placename = "Domestic"
            # Determine if the item is either domestic or rest of the world
            place = next((place for place in (item.get("place") or [])), None)

            if place and place.get(self.GROUP) == "Rest Of World":
                row = True
                placename = place.get(self.NAME, "Domestic")
            else:
                row = False
            # Find if there are other sluglines in this items family
            newer, older_slugline = await self._find_other_sluglines(
                item.get(FAMILY_ID), slugline, item.get(self.VERSION_CREATED), lookup["task.desk"]
            )
            # there are no newer sluglines than the current one
            if not newer:
                if row:
                    self._add_slugline_to_places(
                        row_docs, placename, slugline, headline, older_slugline, versioncreated
                    )
                else:
                    self._add_slugline_to_places(docs, placename, slugline, headline, older_slugline, versioncreated)

        docs.extend(row_docs)
        items = []

        # group by place and sort all items of a place by versioncreated.
        for key, group in itertools.groupby(docs, lambda x: x["name"]):
            items.append({"place": key, "items": sorted(group, key=lambda k: k["versioncreated"], reverse=True)})

        desk_items.docs = items
        return desk_items

    def _add_slugline_to_places(self, places, placename, slugline, headline, old_sluglines, versioncreated):
        """Add slugline to places.

        Append a dictionary to the list, with place holders for the place name and slugline if they are already
        present.

        :param places:
        :param placename:
        :param slugline:
        :param headline:
        :param is_legal:
        :param old_sluglines:
        :param versioncreated:
        :return:
        """
        places.append(
            {
                self.NAME: placename,
                self.SLUGLINE: (
                    slugline
                    if not any(self._get_slugline_with_legal(p).lower() == slugline.lower() for p in places)
                    else "-"
                ),
                self.HEADLINE: headline,
                self.OLD_SLUGLINES: old_sluglines,
                self.VERSION_CREATED: versioncreated,
            }
        )

    async def _find_other_sluglines(self, family_id, slugline, versioncreated, desk_id):
        """Find other sluglines.

        This function given a family_id will return a tuple with the first value true if there is
         a more recent story in the family, the second value in the tuple will be a list of any sluglines
         that might exist for the family that are different to the one passed.

        :param family_id:
        :param slugline:
        :param versioncreated:
        :param desk_id:
        :return: A tuple as described above
        """
        older_sluglines = []
        req = ParsedRequest()
        query = {
            "query": {
                "filtered": {
                    "filter": {
                        "and": [
                            {"term": {"family_id": family_id}},
                            {"term": {"task.desk": desk_id}},
                        ]
                    }
                }
            }
        }
        req.args = {"source": json.dumps(query), "aggregations": 0}
        family = await superdesk.get_resource_service("published").get_async(req=req, lookup=None)
        async for member in family:
            member_slugline = self._get_slugline_with_legal(member)
            if member_slugline.lower() != slugline.lower():
                if member.get("versioncreated") < versioncreated:
                    if member_slugline not in older_sluglines:
                        older_sluglines.append(member_slugline)
                else:
                    return (True, [])
        return (False, older_sluglines)


class OverviewResource(Resource):
    url = r'desks/<regex("([a-f0-9]{24})|all"):desk_id>/overview/<regex("stages|assignments|users"):agg_type>'
    privileges = {"POST": "desks"}
    resource_title = "desk_overview"
    resource_methods = ["GET", "POST"]
    schema = {
        "filters": {
            "type": "dict",
            "schema": {
                "slugline": {"type": "list", "mapping": {"type": "string"}},
                "headline": {"type": "list", "mapping": {"type": "string"}},
                "byline": {"type": "list", "mapping": {"type": "string"}},
            },
        }
    }
    datasource = {"projection": {"_items": 1}}


class OverviewService(AsyncBaseService):
    """Aggregate count of items per stage or status"""

    async def _do_request(self, doc):
        desk_id = request.view_args["desk_id"]
        agg_type = request.view_args["agg_type"]
        timer_label = f"{agg_type} overview aggregation {desk_id!r}"
        if agg_type == "users":
            with timer(timer_label):
                doc["_items"] = await self._users_aggregation(desk_id)
            return

        if agg_type == "stages":
            collection = "archive"
            desk_field = "task.desk"
            key = "stage"
            field = f"task.{key}"
        elif agg_type == "assignments":
            collection = "assignments"
            desk_field = "assigned_to.desk"
            key = "desk"
            field = "assigned_to.desk"
        else:
            raise ValueError(f"Invalid overview aggregation type: {agg_type}")

        agg_query = {
            "filter": {
                "bool": {
                    "must_not": [
                        {
                            "terms": {
                                ITEM_STATE: [
                                    CONTENT_STATE.PUBLISHED,
                                    CONTENT_STATE.SPIKED,
                                    CONTENT_STATE.KILLED,
                                    CONTENT_STATE.CORRECTED,
                                    CONTENT_STATE.SCHEDULED,
                                    CONTENT_STATE.RECALLED,
                                ]
                            }
                        },
                        {"term": {"version": 0}},
                    ]
                }
            }
        }
        filter_bool = agg_query["filter"]["bool"]

        if desk_id != "all":
            filter_bool["must"] = [{"term": {desk_field: desk_id}}]

        # FIXME: we use max size to get all items, but using a composite request with pagination
        #   would be better (cf. https://www.elastic.co/guide/en/elasticsearch/reference/7.11/search-aggregations-bucket
        #                        -composite-aggregation.html)
        agg_query["aggs"] = {"overview": {"terms": {"field": field, "size": SIZE_MAX}}}

        if agg_type == "assignments":
            agg_query["aggs"]["overview"]["aggs"] = {"sub": {"terms": {"field": "assigned_to.state", "size": SIZE_MAX}}}

        filters = doc.get("filters")
        if filters:
            should = []
            filter_bool.setdefault("must", []).append({"bool": {"should": should}})
            for f_name, f_data in filters.items():
                for text in f_data:
                    should.append({"match": {f_name: text}})

        with_docs = request and request.args.get("with_docs") == "1"
        if with_docs:
            agg_query["aggs"]["overview"]["aggs"] = {"top_docs": {"top_hits": {"size": 100}}}

        with timer(timer_label):
            response = get_current_app().data.elastic.search(agg_query, collection, params={"size": 0})

        doc["_items"] = [
            {
                "count": b["doc_count"],
                key: b["key"],
                "sub": format_buckets(b.get("sub")),
            }
            for b in response.hits["aggregations"]["overview"]["buckets"]
        ]

        if with_docs:
            for idx, bucket in enumerate(response.hits["aggregations"]["overview"]["buckets"]):
                docs = doc["_items"][idx]["docs"] = []
                for hit_doc in bucket["top_docs"]["hits"]["hits"]:
                    docs.append(hit_doc["_source"])

    async def on_fetched_async(self, doc):
        await self._do_request(doc)

    async def create_async(self, docs, **kwargs):
        await self._do_request(docs[0])
        return [0]

    async def _users_aggregation(self, desk_id: str) -> List[Dict]:
        desks_service = superdesk.get_resource_service("desks")

        es_query: Dict[str, Any]
        es_assign_query: Dict[str, Any]
        desk_filter: Dict[str, Any]

        if desk_id == "all":
            desk_filter = {}
            es_query = {}
        else:
            desk_filter = {"_id": ObjectId(desk_id)}
            es_query = {"filter": [{"term": {"task.desk": desk_id}}]}

        req = ParsedRequest()
        req.projection = json.dumps({"members": 1})
        found = await desks_service.get_async(req, desk_filter)
        members = set()
        async for d in found:
            members.update({m["user"] for m in d.get("members", [])})

        app = get_current_app()
        users_aggregation = (
            app.data.mongo_async.pymongo("users")
            .db["users"]
            .aggregate(
                [
                    {"$match": {"_id": {"$in": list(members)}}},
                    {"$group": {"_id": "$role", "authors": {"$addToSet": "$_id"}}},
                ]
            )
        )

        # only do aggregations on content accesible by user
        content_filters = superdesk.get_resource_service("search").get_archive_filters()
        if content_filters:
            es_query.setdefault("filter", []).extend(content_filters)

        # first we check archives for locked items
        es_query["aggs"] = {
            "desk_authors": {
                "filter": {"bool": {"filter": {"terms": {"lock_user": [str(m) for m in members]}}}},
                "aggs": {
                    "authors": {
                        "terms": {"field": "lock_user", "size": SIZE_MAX},
                        "aggs": {
                            "locked": {
                                "filter": {
                                    "exists": {
                                        "field": "lock_user",
                                    }
                                }
                            },
                        },
                    }
                },
            }
        }
        docs_agg = app.data.elastic.search(es_query, "archive", params={"size": 0})
        stats_by_authors = {}
        for a in docs_agg.hits["aggregations"]["desk_authors"]["authors"]["buckets"]:
            stats_by_authors[a["key"]] = {
                "locked": a["locked"]["doc_count"],
                "assigned": 0,
            }

        # then assignments
        if desk_id == "all":
            desk_filter = {}
            es_assign_query = {}
        else:
            desk_filter = {"_id": ObjectId(desk_id)}
            es_assign_query = {"filter": {"term": {"assigned_to.desk": desk_id}}}
        es_assign_query["aggs"] = {
            "desk_authors": {
                "filter": {"terms": {"assigned_to.user": [str(m) for m in members]}},
                "aggs": {
                    "authors": {
                        "terms": {"field": "assigned_to.user", "size": SIZE_MAX},
                    }
                },
            }
        }
        try:
            assign_agg = app.data.elastic.search(es_assign_query, "assignments", params={"size": 0})
        except KeyError:
            logger.warning('Can\'t access "assignments" collection, planning is probably not installed')
        else:
            for a in assign_agg.hits["aggregations"]["desk_authors"]["authors"]["buckets"]:
                stats_by_authors.setdefault(a["key"], {"locked": 0})["assigned"] = a["doc_count"]

        overview = []
        async for a in users_aggregation:
            role = a["_id"]
            authors_dict: Dict[str, Any] = {}
            role_dict = {
                "role": role,
                "authors": authors_dict,
            }
            authors = a["authors"]
            for author in authors:
                author = str(author)
                try:
                    authors_dict[author] = stats_by_authors[author]
                except KeyError:
                    logger.debug("No article found for {author}".format(author=author))
                    authors_dict[author] = {"assigned": 0, "locked": 0}
            overview.append(role_dict)

        return overview


async def remove_profile_from_desks_async(item):
    """Removes the profile data from desks that are using the profile

    :param item: deleted content profile
    """
    req = ParsedRequest()
    service = superdesk.get_resource_service("desks")
    desks = await service.get_async(req=req, lookup={})
    async for desk in desks:
        if desk.get("default_content_profile") == str(item.get(ID_FIELD)):
            desk["default_content_profile"] = None
            await service.patch_async(desk[ID_FIELD], desk)


def format_buckets(aggs):
    if not aggs:
        return aggs
    return [
        {
            "key": b["key"],
            "count": b["doc_count"],
        }
        for b in aggs["buckets"]
    ]
