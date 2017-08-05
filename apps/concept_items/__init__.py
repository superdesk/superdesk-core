# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2017 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_backend
import superdesk
from superdesk.services import BaseService

from apps.concept_items.resource import ConceptItemResource,\
    CONCEPT_ITEMS_PRIVILEGE


def init_app(app):
    endpoint_name = 'concept_items'
    service = BaseService(endpoint_name, backend=get_backend())
    ConceptItemResource(endpoint_name, app=app, service=service)

    superdesk.privilege(name=CONCEPT_ITEMS_PRIVILEGE, label='Concept Items Management',
                        description='User can manage concept items.')
