# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging

import click
from pydantic import ValidationError

from superdesk.commands import cli

from superdesk.types import AuthServerClientResource, allowed_auth_server_scopes
from superdesk.core import json
from superdesk.core.resources.validators import get_field_errors_from_pydantic_validation_error


logger = logging.getLogger(__name__)


@cli.command("auth_server:register_client")
@click.argument("name")
@click.option("--client-id", "-i", help="ObjectId compatible client id (keep empty to generate one)")
@click.option("--password", "-p", help="client password (keep empty to generate it)")
@click.option(
    "--scope",
    "-s",
    multiple=True,
    default=[],
    type=click.Choice(allowed_auth_server_scopes),
    help="scopes allowed (one or more of {allowed_scopes})".format(
        allowed_scopes=", ".join(allowed_auth_server_scopes)
    ),
)
async def cli_auth_server_register_client(name, client_id, password, scope):
    """Register a client to authentication server

    A client name is needed, and an id and password will be generated and displayed once
    the client is registered.

    The client will be allowed to access the given scopes using the ``--scope`` argument
    (this argument may be used several times).

    Example:
    Register a new client with name ``my Superdesk client`` and allowed to reach items in archive and get users::

        $ python manage.py auth_server:register_client "my Superdesk client" -s ARCHIVE_READ -s USERS_READ

    """

    try:
        clients = await AuthServerClientResource.get_service().create(
            [AuthServerClientResource(id=client_id, name=name, password=password, scope=scope)]
        )
        client = clients[0]
        print(f"Client {client.name} has been registered with id '{client.id}' and password {client.password}")
    except ValidationError as error:
        errors = {
            field_name: list(field_errors.values())
            for field_name, field_errors in get_field_errors_from_pydantic_validation_error(error).items()
        }

        raise click.BadParameter("\n" + json.dumps(errors))


@cli.command("auth_server:update_client")
@click.option("--name", "-n", help="change client name")
@click.option("--password", "-p", help="update password (keep empty to re-generate it)")
@click.option(
    "--scope",
    "-s",
    multiple=True,
    default=[],
    type=click.Choice(allowed_auth_server_scopes),
    help="scopes allowed (one or more of {allowed_scopes})".format(
        allowed_scopes=", ".join(allowed_auth_server_scopes)
    ),
)
@click.option("--client-id", "-i", help="ObjectId compatible client id")
async def cli_auth_server_update_client(client_id, password, scope, name):
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

    updates: dict = {"password": password}
    if scope:
        updates["scope"] = scope
    if name is not None and name.strip():
        updates["name"] = name

    try:
        service = AuthServerClientResource.get_service()

        original = await service.find_by_id(client_id)
        if not original:
            raise click.BadParameter(f"Can't find any client with id '{client_id}'")

        updated = await service.update(client_id, updates=updates)
        print("Client successfuly updated with:")
        for key, value in updated:
            if value == getattr(original, key):
                continue
            elif key in {"etag", "updated"}:
                continue
            elif key == "scope":
                print(f"\t{key}: {', '.join(value)}")

            print(f"    {key}: {value}")
    except ValidationError as error:
        errors = {
            field_name: list(field_errors.values())
            for field_name, field_errors in get_field_errors_from_pydantic_validation_error(error).items()
        }

        raise click.BadParameter("\n" + json.dumps(errors))


@cli.command("auth_server:unregister_client")
@click.option("--client-id", "-i", help="ObjectId compatible client id")
async def cli_auth_server_unregister_client(client_id):
    """Remove a previously registered client
    Example:

    Unregister client with id ``0102030405060708090a0b0c``::

        $ python manage.py auth_server:unregister_client 0102030405060708090a0b0c

    """
    service = AuthServerClientResource.get_service()

    client = await service.find_by_id(client_id)
    if not client:
        raise click.BadParameter(f"No client with id '{client_id}'")

    await service.delete(client)
    print(f"Client with id '{client_id}' has been successfuly unregistered")


@cli.command("auth_server:list_clients")
async def cli_auth_server_list_clients():
    """List clients registered with auth server

    The client will be listed with their scopes.

    Example::

        $ python manage.py auth_server:list_clients

    """
    clients_desc = []
    async for client in await AuthServerClientResource.get_service().search({}):
        clients_desc.append(
            "- client {name!r}: id '{client_id}' with scope(s) {scopes}".format(
                name=client.name,
                client_id=client.id,
                scopes=", ".join(client.scope),
            )
        )

    if not clients_desc:
        print("No client currently registered with auth server")
    else:
        print("Following clients are currently registered:\n")
        print("\n".join(clients_desc))
        print()
