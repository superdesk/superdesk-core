from typing import Any, Callable, Tuple, cast

from inspect import isawaitable
from functools import update_wrapper
from asyncio import run

from click import Context, Group, pass_context, echo
from quart.cli import ScriptInfo

from ..flask import Blueprint, AppGroup


def with_appcontext_async(fn: Callable) -> Callable:
    """Wraps a click command with app_context and an event loop

    Allows to use an async function as a click command that is automatically
    run inside an event loop with an app context
    """

    @pass_context
    def decorator(__ctx: Context, *args: Any, **kwargs: Any) -> Any:
        async def _inner() -> Any:
            async with __ctx.ensure_object(ScriptInfo).load_app().app_context():
                try:
                    response = __ctx.invoke(fn, *args, **kwargs)
                    return await response if isawaitable(response) else response
                except RuntimeError as error:
                    if error.args[0] == "Cannot run the event loop while another loop is running":
                        echo(
                            "The appcontext cannot be used with a command that runs an event loop. "
                            "See quart#361 for more details"
                        )
                    raise

        return run(_inner())

    return update_wrapper(decorator, fn)


class AsyncAppGroup(AppGroup):
    """
    An extension of Quart's AppGroup to support registration of asynchronous command handlers.

    This class provides a mechanism to register asynchronous functions as command line commands,
    that are automatically wrapped with the app context (unless ``with_appcontext=False`` is provided).
    """

    def command(self, name: str | None = None, with_appcontext: bool = True, *args: Any, **kwargs: Any) -> Callable:
        """This works exactly like the method of the same name on a regular
        :class:`click.Group` but it wraps callbacks in :func:`with_appcontext`
        if it's enabled by passing ``with_appcontext=True``.
        """

        def decorator(f: Callable) -> Callable:
            if with_appcontext:
                f = with_appcontext_async(f)
            return Group.command(self, name, *args, **kwargs)(f)

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
    blueprint = CommandsBlueprint(blueprint_name, __name__, cli_group=None)

    return blueprint, cast(AsyncAppGroup, blueprint.cli)
