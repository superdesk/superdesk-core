from copy import deepcopy
from quart_babel import gettext as _
from apps.comments import CommentsResource, CommentsService
from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.activity import notify_and_add_activity
from superdesk.users.services import get_display_name

from . import privileges, rundown_items, rundowns


class RundownCommentsResource(CommentsResource):
    schema = deepcopy(CommentsResource.schema)
    schema["item"] = Resource.rel("rundown_items", required=True)
    datasource = {}
    privileges = {method: privileges.RUNDOWNS for method in ["POST", "DELETE"]}


class RundownCommentsService(CommentsService):
    notifications = False

    def on_created(self, docs):
        super().on_created(docs)
        for doc in docs:
            if not doc.get("mentioned_users"):
                continue
            user_ids = list(set(doc["mentioned_users"].values()))
            users = list(get_resource_service("users").find({"_id": {"$in": user_ids}}))
            item = rundown_items.items_service.find_one(req=None, _id=doc["item"])
            user = get_resource_service("users").find_one(req=None, _id=doc["user"])
            rundown = rundowns.rundowns_service.find_one(req=None, _id=item["rundown"])
            assert item is not None
            # TODO-ASYNC: Support async (see superdesk.tests.markers.requires_eve_resource_async_event)
            notify_and_add_activity(
                "rundown-item-comment",
                _(
                    'You were mentioned in "%(item_name)s" ("%(rundown_name)s") comment by %(user)s.',
                    item_name=item["title"],
                    rundown_name=rundown["title"],
                    user=get_display_name(user),
                ),
                resource="rundown_items",
                item=None,
                user_list=users,
                message=doc["text"],
                rundownId=item.get("rundown"),
                rundownItemId=item["_id"],
                extension="broadcasting",
            )


comments_service = RundownCommentsService()
