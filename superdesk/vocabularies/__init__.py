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

from .vocabularies import VocabulariesResource, VocabulariesService
from .commands import UpdateVocabulariesInItemsCommand # noqa


def init_app(app):
    endpoint_name = 'vocabularies'
    service = VocabulariesService(endpoint_name, backend=superdesk.get_backend())
    VocabulariesResource(endpoint_name, app=app, service=service)

    superdesk.register_default_user_preference('cvs:preferred_items', {
        'value': {},
        'category': 'cvs',
        'label': 'Prefered CV items',
    })
