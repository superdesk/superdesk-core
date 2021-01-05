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

from .resource import ConceptItemsResource, CONCEPT_ITEMS_PRIVELEGE
from .service import ConceptItemsService


def init_app(app):
    endpoint_name = "concept_items"
    service = ConceptItemsService(endpoint_name, backend=superdesk.get_backend())
    ConceptItemsResource(endpoint_name, app=app, service=service)

    superdesk.privilege(
        name=CONCEPT_ITEMS_PRIVELEGE, label="Concept items management", description="User can manage concept items."
    )
