# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk.resource import Resource


class MarkedForDesksResource(Resource):
    """Marked for desks Schema"""

    schema = {"marked_desk": {"type": "string", "required": True}, "marked_item": {"type": "string", "required": True}}
    privileges = {"POST": "mark_for_desks"}
