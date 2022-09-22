from apps.comments import CommentsResource, CommentsService

from . import privileges


class RundownCommentsResource(CommentsResource):
    schema = CommentsResource.schema.copy()
    schema["rundown"] = {"type": "string"}
    privileges = {method: privileges.RUNDOWNS for method in ["POST", "DELETE"]}


class RundownCommentsService(CommentsService):
    pass


comments_service = RundownCommentsService()
