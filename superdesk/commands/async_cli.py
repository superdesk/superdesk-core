from functools import wraps
from typing import Any, Callable, Optional, Tuple, cast
from asgiref.sync import async_to_sync

from ..flask import Blueprint, AppGroup, Flask


class AsyncAppGroup(AppGroup):
    """
    An extension of Quart's AppGroup to support registration of asynchronous command handlers.

    This class provides a mechanism to register asynchronous functions as command line commands,
    which are automatically handled synchronously using `asgiref.sync.async_to_sync` conversion.
    """

    app: Flask

    def register_async_command(
        self, name: Optional[str] = None, with_appcontext=False, **click_kwargs: dict[str, Any]
    ) -> Callable[..., Any]:
        """
        A decorator to register an asynchronous command within the Quart CLI app group.
        If your command needs to use the app context, pass `with_appcontext=True` to ensure it will be run
        wrapped with current app context. Otherwise getting current app context will fail in asynchronous
        command contexts due to execution in different threads or outside of the normal request context lifecycle.

        Args:
            name (str, optional): The name of the command. Defaults to the function's name if None.
            with_appcontext (bool): If True, it will wrap the command function in the current_app's context.
                                    Note that `set_current_app` method has to be called first.
            **click_kwargs: Additional keyword arguments that are passed to the `AppGroup.command` decorator.

        Example:
        Use the decorator to register a command that requires app context:

        .. code-block:: python

            from superdesk.commands import cli

            @cli.register_async_command("example-command", with_appcontext=True)
            async def my_command():
                app = get_current_app()
                with app.app_context():
                    # your command logic here
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            # This wrapper will convert the async function to a sync function
            # using async_to_sync when the command is actually called.
            def sync_wrapper(*args, **kwargs) -> Any:
                if with_appcontext:
                    return async_to_sync(self.run_with_appcontext)(func, *args, **kwargs)
                return async_to_sync(func)(*args, **kwargs)

            return self.command(name, **click_kwargs)(sync_wrapper)

        return decorator

    async def run_with_appcontext(self, func: Callable[..., Any], *args, **kwargs):
        current_app = self.get_current_app()
        if current_app is None:
            raise RuntimeError("No app instance available. Make sure to run `set_current_app(app_instance)` first.")

        async with current_app.app_context():
            return await func(*args, **kwargs)

    def set_current_app(self, app: Flask):
        """
        Sets current app instance so it can be passed down to commands if needed
        """
        self.app = app

    def get_current_app(self) -> Flask:
        return self.app


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


commands_blueprint, cli = create_commands_blueprint("superdesk")
