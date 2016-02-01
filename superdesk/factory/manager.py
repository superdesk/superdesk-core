
import superdesk
from flask.ext.script import Manager


class SuperdeskManager():
    """Superdesk scripts manager."""

    def __init__(self, app, commands):
        self.manager = Manager(app)
        self.commands = commands

    def run(self):
        """Run manager with predefined set of commands."""
        self.manager.run(self.commands)


def get_manager(app):
    """Get instance of superdesk manager with registered commands.

    :param app: superdesk app instance
    """
    return SuperdeskManager(app, superdesk.COMMANDS)
