from superdesk.flask import Flask
import superdesk


class SuperdeskManager:
    """Superdesk scripts manager."""

    def __init__(self, app, commands):
        self.app = app
        self.commands = commands

    def add_commands_to_cli(self):
        for command in self.commands:
            self.app.cli.add_command(command())

    def run(self):
        """Run manager with predefined set of commands."""

        self.add_commands_to_cli()

        with self.app.app_context():
            self.app.cli.main()


def get_manager(app: Flask):
    """Get instance of superdesk manager with registered commands.

    :param app_factory: superdesk app factory function
    """

    return SuperdeskManager(app, superdesk.COMMANDS_V2)


if __name__ == "__main__":
    from .app import get_app
    import superdesk.commands

    app = get_app()
    get_manager(app).run()
