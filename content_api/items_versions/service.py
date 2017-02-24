# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license
from eve.utils import ParsedRequest, config
from eve.versioning import versioned_id_field
from superdesk.services import BaseService
from flask import current_app as app
from superdesk.utils import ListCursor


class ItemsVersionsService(BaseService):

    def get(self, req, lookup):
        resource_def = app.config['DOMAIN']['items']
        id_field = versioned_id_field(resource_def)

        if req and req.args and req.args.get(config.ID_FIELD):
            version_history = list(super().get_from_mongo(req=ParsedRequest(),
                                                          lookup={id_field: req.args.get(config.ID_FIELD)}))
        else:
            version_history = list(super().get_from_mongo(req=req, lookup=lookup))

        for doc in version_history:
            doc[config.ID_FIELD] = doc[id_field]

        return ListCursor(version_history)
