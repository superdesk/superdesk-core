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


class DesksService(ProdApiService):
    excluded_fields = \
        {
            'default_content_template',
            'working_stage',
            'incoming_stage',
            'desk_metadata',
            'content_expiry',
        } | ProdApiService.excluded_fields
