# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2016 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from alchemyapi import AlchemyAPI


class AlchemyEngine:
    def query(self, doc):
        pass
#         if 'text' in doc:
#             alchemy_api.keywords('text', doc['text'])


from apps.analytics.engines import register_engine
register_engine('alchemy', AlchemyEngine())
