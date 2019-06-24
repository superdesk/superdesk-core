# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
from pathlib import Path
from importlib import import_module
from superdesk.resource import Resource
from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError
from .base import registered_spellcheckers, SpellcheckerBase
from inspect import isclass
import superdesk

logger = logging.getLogger(__name__)
# can be set to False if importSpellcheckers need to be called manually
# (e.g. in unit tests)
AUTO_IMPORT = True


class SpellcheckerResource(Resource):
    schema = {
        'spellchecker': {
            'type': 'string',
            'required': True,
        },
        'text': {
            'type': 'string',
            'required': True,
        },
        'suggestions': {
            'type': 'boolean',
            'default': False,
        },
    }
    internal_resource = False
    resource_methods = ['POST']
    item_methods = ['GET']


class SpellcheckerService(BaseService):

    def create(self, docs, **kwargs):
        # we override create because we don't want anything stored in database
        doc = docs[0]
        sc_name = doc["spellchecker"]
        try:
            spellchecker = registered_spellcheckers[sc_name]
        except KeyError:
            raise SuperdeskApiError.notFoundError("{sc_name} spellchecker can't be found".format(sc_name=sc_name))

        if doc["suggestions"]:
            check_data = spellchecker.suggest(doc['text'])
            assert "suggestions" in check_data
        else:
            check_data = spellchecker.check(doc['text'])
            assert "errors" in check_data
        docs[0].update(check_data)
        return [0]


class SpellcheckersListResource(Resource):
    pass


class SpellcheckersListService(BaseService):
    """Service listing registered spell checkers"""

    def on_fetched(self, doc):
        doc['spellcheckers'] = [s.serialize() for s in registered_spellcheckers.values()]


def importSpellcheckers(app, pkg_name):
    """Import all spellcheckers in given package

    This method will import python modules and look for a SpellcheckerBase subclass there
    If found, the subclass will be instanciated
    :param app: app instance
    :param str pkg_name: name of the package to use
    """
    pkg = import_module(pkg_name)
    for file_path in Path(pkg.__file__).parent.glob("*.py"):
        module_name = file_path.stem
        if module_name in ("__init__", "base"):
            continue
        spellchecker_mod = import_module(pkg_name + '.' + module_name)
        for obj_name in dir(spellchecker_mod):
            if obj_name.startswith('__') or obj_name == 'SpellcheckerBase':
                continue
            obj = getattr(spellchecker_mod, obj_name)
            if not isclass(obj):
                continue
            if issubclass(obj, SpellcheckerBase):
                obj(app)
                break
        else:
            logger.warning("Can't find Spellchecker in module {module_name}".format(module_name=module_name))


def init_app(app):
    endpoint_name = 'spellcheckers_list'
    service = SpellcheckersListService(endpoint_name, backend=superdesk.get_backend())
    SpellcheckersListResource(endpoint_name, app=app, service=service)

    endpoint_name = 'spellchecker'
    service = SpellcheckerService(endpoint_name, backend=superdesk.get_backend())
    SpellcheckerResource(endpoint_name, app=app, service=service)
    superdesk.intrinsic_privilege(endpoint_name, method=['POST'])

    if AUTO_IMPORT:
        importSpellcheckers(app, __name__)
