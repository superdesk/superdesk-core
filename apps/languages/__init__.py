# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_backend
from superdesk.metadata.utils import aggregations
from apps.languages.service import LanguagesService
from apps.languages.resource import LanguagesResource


def init_app(app) -> None:
    endpoint_name = "languages"
    service = LanguagesService(endpoint_name, backend=get_backend())
    LanguagesResource(endpoint_name, app=app, service=service)

    # add language to aggregations
    aggregations.update(
        {
            "language": {"terms": {"field": "language"}},
        }
    )
