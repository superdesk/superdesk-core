# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import sys
import logging
import bcrypt
from bson import ObjectId
from bson.errors import InvalidId
import superdesk
from superdesk.utils import gen_password
from superdesk.auth_server.scopes import allowed_scopes


logger = logging.getLogger(__name__)


class AuthServerClientsResource(superdesk.Resource):

    schema = {
        "name": {
            "type": "string",
            "required": True,
            "unique": True,
        },
        "password": {"type": "string", "required": True},
        "scope": {"type": "list", "allowed": list(allowed_scopes), "required": True},
    }


class AuthServerClientsService(superdesk.Service):
    """Service to handle authorization server clients"""


class CommonClient:
    """Common method for client commands"""

    def validate_scope(self, scope):
        """Return list of unique and valid scopes, end command execution else"""
        scope = set(scope)
        if not scope.issubset(allowed_scopes):
            self.parser.error(
                "invalid scopes: {invalid_scopes}\nvalid scopes are: {allowed_scopes}".format(
                    invalid_scopes=", ".join(scope - allowed_scopes), allowed_scopes=", ".join(allowed_scopes)
                )
            )
        return list(scope)


class RegisterClient(superdesk.Command, CommonClient):
    """Register a client to authentication server

    A client name is needed, and an id and password will be generated and displayed once
    the client is registered.

    The client will be allowed to access the given scopes using the ``--scope`` argument
    (this argument may be used several times).

    Example:
    Register a new client with name ``my Superdesk client`` and allowed to reach items in archive and get users::

        $ python manage.py auth_server:register_client "my Superdesk client" -s ARCHIVE_READ -s USERS_READ

    """

    option_list = [
        superdesk.Option(
            "--client-id", "-i", dest="client_id", help="ObjectId compatible client id (keep empty to generate one)"
        ),
        superdesk.Option("--password", "-p", nargs="?", const="", help="client password (keep empty to generate it)"),
        superdesk.Option(
            "--scope",
            "-s",
            action="append",
            default=[],
            help="scopes allowed (one or more of {allowed_scopes})".format(allowed_scopes=", ".join(allowed_scopes)),
        ),
        # empty string is used to request a password prompt
        superdesk.Option("name"),
    ]

    def run(self, client_id, password, scope, name):
        self.validate_name(name)
        scope = self.validate_scope(scope)

        if client_id is None:
            client_id = ObjectId()
        else:
            client_id = self.validate_client_id(client_id)

        if not password or not password.strip():
            password = gen_password()

        client_data = {
            "_id": client_id,
            "name": name,
            "password": bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
            "scope": list(scope),
        }

        superdesk.get_resource_service("auth_server_clients").post([client_data])
        print(
            "Client {name!r} has been registered with id '{client_id}' and password {password!r}".format(
                name=name, client_id=client_id, password=password
            )
        )

    def validate_client_id(self, client_id):
        """
        Validate client id string and return client id ObjectId
        :param client_id: client id
        :type client_id: str
        :return: client id
        :rtype: ObjectId
        """

        try:
            client_id = ObjectId(client_id)
        except InvalidId as e:
            self.parser.error("the given client id is not valid: {msg}".format(msg=e))

        try:
            next(superdesk.get_resource_service("auth_server_clients").find({"_id": client_id}))
        except StopIteration:
            pass
        else:
            self.parser.error("a client with this id already exists!")

        return client_id

    def validate_name(self, name):
        """
        Validate name
        :param name: client name
        :type name: str
        """

        if not name.strip():
            self.parser.error("please enter a valid name")

        try:
            next(superdesk.get_resource_service("auth_server_clients").find({"name": name}))
        except StopIteration:
            pass
        else:
            self.parser.error("a client with this name already exists!")


class UpdateClient(superdesk.Command, CommonClient):
    """Update an existing client

    You need to specify the client ID to update. Specify the parameters that you want to
    update. You can use ``--password`` to set a new password, keep empty to generate a new
    password.

    Examples:
    Change name of client with id ````:

        $ python manage.py auth_server:update_client 0102030405060708090a0b0c --name "some new name"

    Regenerate password of client with id ``5dad7ee94269dd1d5a78e6a1``:

        $ python manage.py auth_server:update_client 5dad7ee94269dd1d5a78e6a1 --password

    Change scope of client with id ``5dad7f064269dd1d5a78e6a2`` to allow only ARCHIVE_READ::

        $ python manage.py auth_server:update_client 5dad7f064269dd1d5a78e6a2 -s ARCHIVE_READ

    """

    option_list = [
        superdesk.Option("--name", "-n", help="change client name"),
        # empty string is used to re-generate password
        superdesk.Option(
            "--password", "-p", nargs="?", const="", help="update password (keep empty to re-generate it)"
        ),
        superdesk.Option(
            "--scope",
            "-s",
            action="append",
            default=[],
            help="scopes allowed (one or more of {allowed_scopes})".format(allowed_scopes=", ".join(allowed_scopes)),
        ),
        superdesk.Option("client_id"),
    ]

    def run(self, client_id, password, scope, name):
        clients_service = superdesk.get_resource_service("auth_server_clients")
        try:
            client_id = ObjectId(client_id)
        except InvalidId as e:
            self.parser.error("the given client id is not valid: {msg}".format(msg=e))

        try:
            original_client = next(clients_service.find({"_id": client_id}))
        except StopIteration:
            self.parser.error("Can't find any client with id '{client_id}'".format(client_id=client_id))

        client_updates = {}

        if name is not None and name.strip():
            client_updates["name"] = name

        if password is not None:
            if not password.strip():
                password = gen_password()
            client_updates["password"] = (bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),)

        if scope:
            client_updates["scope"] = self.validate_scope(scope)

        clients_service.update(original_client["_id"], client_updates.copy(), original_client)

        print("Client successfuly updated with:")
        for key, value in client_updates.items():
            if key == "scope":
                print("    {key}: {value}".format(key=key, value=", ".join(value)))
                continue
            elif key == "password":
                value = password

            print("    {key}: {value!r}".format(key=key, value=value))


class UnregisterClient(superdesk.Command):
    """Remove a previously registered client
    Example:

    Unregister client with id ``0102030405060708090a0b0c``::

        $ python manage.py auth_server:unregister_client 0102030405060708090a0b0c

    """

    option_list = [
        superdesk.Option("client_id"),
    ]

    def run(self, client_id):
        try:
            client_id = ObjectId(client_id)
        except InvalidId as e:
            self.parser.error("the given client id is not valid: {msg}".format(msg=e))
        clients_service = superdesk.get_resource_service("auth_server_clients")
        client = clients_service.find_one(req=None, _id=client_id)
        if client is None:
            print("No client with id '{client_id}' found".format(client_id=client_id))
            sys.exit(2)

        clients_service.delete({"_id": client_id})
        print("Client with id '{client_id}' has been successfuly unregistered".format(client_id=client_id))


class ListClients(superdesk.Command):
    """List clients registered with auth server

    The client will be listed with their scopes.

    Example::

        $ python manage.py auth_server:list_clients

    """

    def run(self):
        clients_service = superdesk.get_resource_service("auth_server_clients")
        clients_desc = []
        for client in clients_service.find({}):
            clients_desc.append(
                "- client {name!r}: id '{client_id}' with scope(s) {scopes}".format(
                    name=client["name"],
                    client_id=client["_id"],
                    scopes=", ".join(client["scope"]),
                )
            )

        if not clients_desc:
            print("No client currently registered with auth server")
        else:
            print("Following clients are currently registered:\n")
            print("\n".join(clients_desc))
            print()


superdesk.command("auth_server:register_client", RegisterClient())
superdesk.command("auth_server:update_client", UpdateClient())
superdesk.command("auth_server:unregister_client", UnregisterClient())
superdesk.command("auth_server:list_clients", ListClients())
