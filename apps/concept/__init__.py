# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import logging
import superdesk
from .service import ConceptService
from .resource import ConceptResource, CONCEPT_PRIVILEGE

logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = 'concept'
    service = ConceptService(endpoint_name, backend=superdesk.get_backend())
    ConceptResource(endpoint_name, app=app, service=service)
    superdesk.privilege(name=CONCEPT_PRIVILEGE, label='Manage Concepts', description='Manage Concepts')
