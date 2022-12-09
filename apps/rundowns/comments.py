from copy import deepcopy
from apps.comments import CommentsResource, CommentsService
from superdesk.resource import Resource
from superdesk.notification import push_notification

from . import privileges


class RundownCommentsResource(CommentsResource):
    schema = deepcopy(CommentsResource.schema)
    schema["item"] = Resource.rel("rundown_items", nullable=True)
    schema["rundown"] = Resource.rel("rundowns", nullable=True)
    datasource = {}
    privileges = {method: privileges.RUNDOWNS for method in ["POST", "DELETE"]}


class RundownCommentsService(CommentsService):
    def on_created(self, docs):
        super().on_created(docs)
        for doc in docs:
            push_notification(
                "rundown-item-comment",
                message=doc["text"],
                rundownId=doc.get("rundown"),
                rundownItemId=doc.get("item"),
                extension="broadcasting",
            )


comments_service = RundownCommentsService()
