# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk

from superdesk.signals import item_published
from .vocabularies import VocabulariesResource, VocabulariesService, is_related_content
from .commands import UpdateVocabulariesInItemsCommand  # noqa
from .keywords import add_missing_keywords
from quart_babel import lazy_gettext


def init_app(app) -> None:
    endpoint_name = "vocabularies"
    service = VocabulariesService(endpoint_name, backend=superdesk.get_backend())
    VocabulariesResource(endpoint_name, app=app, service=service)

    superdesk.register_default_user_preference(
        "cvs:preferred_items",
        {
            "value": {},
        },
        label=lazy_gettext("Prefered CV items"),
        category=lazy_gettext("cvs"),
    )

    item_published.connect(add_missing_keywords)
