# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource
from superdesk.metadata.utils import item_url
from superdesk.auth_server.scopes import Scope
from apps.contacts.resource import ContactsResource as _ContactsResource


class ContactsResource(Resource):
    url = "contacts"
    item_url = item_url
    item_methods = ["GET"]
    resource_methods = ["GET"]
    schema = _ContactsResource.schema.copy()
    datasource = {
        "source": "contacts",
        "search_backend": "elastic",
        "default_sort": [("last_name.keyword", 1)],
        "projection": {"fields_meta": 0},
    }
    privileges = {"GET": Scope.CONTACTS_READ.name}
