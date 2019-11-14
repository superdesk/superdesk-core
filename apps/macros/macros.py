# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license


import superdesk

from superdesk.errors import SuperdeskApiError
from superdesk.utils import ListCursor
from .macro_register import macros


def get_public_props(item):
    return {k: v for k, v in item.items() if k != 'callback'}


class MacrosService(superdesk.Service):

    def get(self, req, lookup):
        """Return all registered macros."""
        desk = getattr(req, 'args', {}).get('desk')
        include_backend = getattr(req, 'args', {}).get('backend') == 'true'
        all_macros = self.get_macros(include_backend)

        if desk:
            return ListCursor([get_public_props(macro) for macro in all_macros if
                               desk.upper() in macro.get('desks', []) or macro.get('desks') is None])
        else:
            return ListCursor([get_public_props(macro) for macro in all_macros])

    def create(self, docs, **kwargs):
        try:
            ids = []
            for doc in docs:
                res = self.execute_macro(doc['item'], doc['macro'])
                if isinstance(res, tuple):
                    doc['item'] = res[0]
                    doc['diff'] = res[1]
                else:
                    doc['item'] = res
                if doc.get('commit'):
                    item = superdesk.get_resource_service('archive').find_one(req=None, _id=doc['item']['_id'])
                    updates = doc['item'].copy()
                    updates.pop('_id')
                    superdesk.get_resource_service('archive').update(item['_id'], updates, item)
                ids.append(doc['macro'])
            return ids
        except Exception as ex:
            raise SuperdeskApiError.internalError(str(ex), exception=ex)

    def get_macro_by_name(self, macro_name):
        return macros.find(macro_name)

    def execute_macro(self, doc, macro_name, **kwargs):
        macro = self.get_macro_by_name(macro_name)
        return macro['callback'](doc, **kwargs)

    def get_macros(self, include_backend):
        if include_backend:
            return macros
        else:
            return [m for m in macros if m.get('access_type') == 'frontend']

    def execute_translation_macro(self, doc, from_language, to_language):
        """
        Apply to doc all macros that are related to current translation defined by from_language and to_language
        Macros can have optionally defined translation related settings: from_languages, to_languages.
        """
        for m in macros:
            if (not m.get('from_languages', None) or from_language in m['from_languages']) \
                    and to_language in m.get('to_languages', []):
                m['callback'](doc, from_language=from_language, to_language=to_language)


class MacrosResource(superdesk.Resource):
    resource_methods = ['GET', 'POST']
    item_methods = []
    privileges = {'POST': 'archive'}

    schema = {
        'macro': {
            'type': 'string',
            'required': True,
            'allowed': macros
        },
        'item': {
            'type': 'dict',
        },
        'commit': {
            'type': 'boolean',
            'default': False,
        },
        'diff': {
            'type': 'dict',
            'readonly': True,
        },
    }
