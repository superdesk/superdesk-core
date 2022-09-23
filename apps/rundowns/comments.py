from apps.comments import CommentsResource, CommentsService
from superdesk.resource import Resource

from . import privileges


class RundownCommentsResource(CommentsResource):
    schema = CommentsResource.schema.copy()
    schema["item"] = Resource.rel("rundown_items", nullable=True)
    schema["rundown"] = Resource.rel("rundowns", nullable=True)
    privileges = {method: privileges.RUNDOWNS for method in ["POST", "DELETE"]}


class RundownCommentsService(CommentsService):
    pass


comments_service = RundownCommentsService()
