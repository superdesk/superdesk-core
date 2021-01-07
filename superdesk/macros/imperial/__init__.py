import os

from superdesk.macros import load_macros


def init_app(app):
    load_macros(os.path.dirname(__file__), __name__)
