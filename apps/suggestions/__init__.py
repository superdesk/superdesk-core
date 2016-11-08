# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from apps.keywords.alchemy import AlchemyKeywordsProvider
from superdesk import get_backend

from apps.suggestions.resource import SuggestionsResource
from apps.suggestions.service import SuggestionsService


def init_app(app):
    endpoint_name = 'suggestions'
    service = SuggestionsService(endpoint_name, backend=get_backend())
    if app.config.get('KEYWORDS_PROVIDER') == 'Alchemy':
        service.provider = AlchemyKeywordsProvider()
    SuggestionsResource(endpoint_name, app=app, service=service)
