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

from eve.utils import config

from superdesk.services import BaseService
from superdesk.errors import SuperdeskApiError


logger = logging.getLogger(__name__)


class PublishService(BaseService):
    """A service for publishing to the content api.

    Serves mainly as a proxy to the data layer.
    """

    def create(self, docs, **kwargs):
        ids = []
        for doc in docs:
            ids.extend(self._create_doc(doc, **kwargs))
        return ids

    def _create_doc(self, doc, **kwargs):
        _id = doc[config.ID_FIELD] = doc.pop('guid')
        original = self.find_one(req=None, _id=_id)
        self._process_associations(doc)
        if original:
            self.update(_id, doc, original)
            return _id
        else:
            return super().create([doc], **kwargs)

    def _process_associations(self, doc):
        if 'associations' in doc:
            for group, assoc in doc['associations'].items():
                if type(assoc) != dict:
                    msg = "Associations group %s has invalid value in list: '%s', should be dictionary" \
                        % (group, assoc)
                    raise SuperdeskApiError.badRequestError(msg)
                # if then association dictionary contains more than 2 items
                # (_id, type) then it's an embedded item
                if len(assoc) > 2:
                    self._create_doc(assoc)
                    for key in list(assoc):
                        if key != config.ID_FIELD and key != 'type':
                            del assoc[key]
