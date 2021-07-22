# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from flask_babel import lazy_gettext
import superdesk
from apps.dictionaries.resource import DictionariesResource
from apps.dictionaries.service import DictionaryService


def init_app(app) -> None:
    endpoint_name = "dictionaries"
    service = DictionaryService(endpoint_name, backend=superdesk.get_backend())
    DictionariesResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name="dictionaries",
        label=lazy_gettext("Dictionaries List Management"),
        description=lazy_gettext("User can manage dictionaries lists."),
    )
