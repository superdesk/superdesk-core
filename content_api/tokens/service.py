# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

import superdesk
from datetime import timedelta
from superdesk.utc import utcnow
from superdesk.utils import get_random_token


class CompanyTokenService(superdesk.Service):
    def create(self, docs, **kwargs):
        for doc in docs:
            doc["_id"] = get_random_token()
            doc.setdefault("expiry", utcnow() + timedelta(days=7))
        return super().create(docs, **kwargs)
