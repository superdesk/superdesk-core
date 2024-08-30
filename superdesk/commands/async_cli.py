from typing import Tuple
from functools import wraps
from asgiref.sync import async_to_sync

from ..flask import Blueprint, AppGroup


class AsyncAppGroup(AppGroup):
    """
    An extension of Quart's AppGroup to support registration of asynchronous command handlers.

    This class provides a mechanism to register asynchronous functions as command line commands,
    which are automatically handled synchronously using `asgiref.sync.async_to_sync` conversion.
    """

    def register_async_command(self, name=None, **click_kwargs):
        """
        A decorator to register an asynchronous command within the Quart CLI app group.

        Args:
            name (str): The name of the command. If None, the function's name will be used.
            **click_kwargs: Arbitrary keyword arguments that are passed to the `AppGroup.command` decorator.

        Returns:
            function: A decorator that wraps the async function and registers it as a command.
        """

        def decorator(func):
            @wraps(func)
            # This wrapper will convert the async function to a sync function
            # using async_to_sync when the command is actually called.
            def sync_wrapper(*args, **kwargs):
                return async_to_sync(func)(*args, **kwargs)

            # register the sync wrapper as a click command
            click_command = self.command(name, **click_kwargs)
            return click_command(sync_wrapper)

        return decorator


class CommandsBlueprint(Blueprint):
    """
    Custom Blueprint that integrates AsyncAppGroup to register CLI commands that are asynchronous,
    allowing them to be used in a synchronous context by Quart's command line interface.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cli = AsyncAppGroup()


def create_commands_blueprint(blueprint_name: str) -> Tuple[CommandsBlueprint, AsyncAppGroup]:
    """
    Create a Blueprint to organize all superdesk commands.

    By setting cli_group=None, any new CLI commands added to this blueprint
    will still be compatible with the existing `python manage.py <command-name>`
    format.

    Returns:
        Tuple[Blueprint, AppGroup]: A tuple containing the configured Blueprint
        object and its associated CLI AppGroup for command registration.
    """
    blueprint = CommandsBlueprint(blueprint_name, __name__)

    return blueprint, blueprint.cli


commands_blueprint, cli = create_commands_blueprint("superdesk")
