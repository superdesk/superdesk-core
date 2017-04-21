#
import superdesk

from flask_script import Manager
from superdesk.factory import get_app


def main():
    app = get_app()
    manager = Manager(app)
    manager.run(superdesk.COMMANDS)


if __name__ == '__main__':
    main()
