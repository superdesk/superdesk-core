from superdesk.resource import Resource
from superdesk.metadata.utils import item_url
from superdesk.types import AuthServerScope


class UsersResource(Resource):
    url = "users"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    allow_unknown = True
    datasource = {"source": "users", "default_sort": [("username", 1)]}
    privileges = {"GET": AuthServerScope.USERS_READ.name}
