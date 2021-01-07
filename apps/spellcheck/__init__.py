from .spellcheck import SpellcheckService, SpellcheckResource
from .tansa import init_app as init_tansa


def init_app(app):
    endpoint_name = "spellcheck"
    service = SpellcheckService(endpoint_name, backend=None)
    SpellcheckResource(endpoint_name, app=app, service=service)
    init_tansa(app)
