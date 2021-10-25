from superdesk.resource import Resource
from superdesk.metadata.utils import item_url
from superdesk.auth_server.scopes import Scope


class UsersResource(Resource):
    url = "users"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    allow_unknown = True
    datasource = {"source": "users", "default_sort": [("username", 1)]}
    privileges = {"GET": Scope.USERS_READ.name}
