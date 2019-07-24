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
# default spellchecker is the basic one, using internal dictionary
SPELLCHECKER_DEFAULT = "default"
CAP_SPELLING = "spelling"
CAP_GRAMMAR = "grammar"
# any language is supported
LANG_ANY = "*"


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
        'language': {
            'type': 'string',
            'nullable': True,
        },
        'suggestions': {
            'type': 'boolean',
            'default': False,
        },
        # if True, spelling errors which are in internal dictionary will be ignored
        'use_internal_dict': {
            'type': 'boolean',
            'default': True,
        },
    }
    internal_resource = False
    resource_methods = ['POST']
    item_methods = ['GET']


class SpellcheckerService(BaseService):
    r"""Service managing spellchecking and suggestions.

    When doing a POST request on this service, the following keys can be used (keys with a \* are required):


    =================   ===========
    key                 explanation
    =================   ===========
    spellchecker \*     name of the spellchecker
    text \*             text to check or word for suggestions
    language            language to use (for spellcheckers handling several ones)
    suggestions         false (default) to check a text, else will get suggestions
    use_internal_dict   true (default) to remove spellings mistakes from words in personal dictionary
    =================   ===========

    e.g. to check a French text while removing words from personal dictionary (grammar mistakes are here on purpose):

    .. sourcecode:: json

        {
            "spellchecker": "grammalecte",
            "text": "Il nous reste à vérifié votre maquette."
        }

    Here is an example payload for suggestions:

    .. sourcecode:: json

        {
            "spellchecker": "grammalecte",
            "suggestions": true,
            "text": "fote"
        }

    """

    def remove_errors_in_dict(self, spellchecker, language, check_data):
        """Remove spelling error which are in the internal dictionary

        :param SpellcheckerBase: spellchecker used
        :param str language: language specified by the client
        :param dict check_data: data returned by spellchecker.check method (will be modified in place)
        """
        if spellchecker.name == SPELLCHECKER_DEFAULT:
            # default spellchecker already works with internal dictionaries
            return
        errors = check_data['errors']
        if not errors:
            return
        lang = spellchecker.get_language(language)
        dictionaries_service = superdesk.get_resource_service('dictionaries')
        model = dictionaries_service.get_model_for_lang(lang)
        to_remove = []
        for error in errors:
            if error.get('type', 'spelling') != 'spelling':
                continue
            if error['text'].lower() in model:
                to_remove.append(error)
        for error in to_remove:
            errors.remove(error)

    def create(self, docs, **kwargs):
        # we override create because we don't want anything stored in database
        doc = docs[0]
        sc_name = doc["spellchecker"]
        language = doc.get('language')
        try:
            spellchecker = registered_spellcheckers[sc_name]
        except KeyError:
            raise SuperdeskApiError.notFoundError("{sc_name} spellchecker can't be found".format(sc_name=sc_name))

        if doc["suggestions"]:
            check_data = spellchecker.suggest(doc['text'], language)
            assert "suggestions" in check_data
        else:
            check_data = spellchecker.check(doc['text'], language)
            assert "errors" in check_data
            if doc["use_internal_dict"]:
                self.remove_errors_in_dict(spellchecker, language, check_data)
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
