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
from .service import ContactsService, OrganisationService
from .resource import ContactsResource, CONTACTS_PRIVILEDGE, VIEW_CONTACTS, OrganisationSearchResource

logger = logging.getLogger(__name__)


def init_app(app):
    endpoint_name = 'contacts'
    service = ContactsService(endpoint_name, backend=superdesk.get_backend())
    ContactsResource(endpoint_name, app=app, service=service)
    superdesk.privilege(name=CONTACTS_PRIVILEDGE, label='Contacts Management', description='Manage Contacts')
    superdesk.privilege(name=VIEW_CONTACTS, label='Contacts View Rights', description='View Contacts')

    service = OrganisationService(endpoint_name, backend=superdesk.get_backend())
    endpoint_name = 'contacts organisations'
    OrganisationSearchResource(endpoint_name, app=app, service=service)
