from copy import deepcopy
from flask_babel import _
from apps.comments import CommentsResource, CommentsService
from superdesk import get_resource_service
from superdesk.resource import Resource
from superdesk.activity import notify_and_add_activity

from . import privileges, rundown_items


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
            assert item is not None
            notify_and_add_activity(
                "rundown-item-comment",
                _("User was mentioned in rundown item comment."),
                resource="rundown_items",
                item=None,
                user_list=users,
                message=doc["text"],
                rundownId=item.get("rundown"),
                rundownItemId=item["_id"],
                extension="broadcasting",
            )


comments_service = RundownCommentsService()
