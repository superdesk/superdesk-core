# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2019 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from ..service import ProdApiService


class ContactsService(ProdApiService):
    excluded_fields = {
        '_etag',
        '_type',
        '_updated',
        '_created',
        '_links'
    }
